from pathlib import Path
import hashlib

import pandas as pd
from PIL import Image
from tqdm import tqdm


DATA_DIR = Path("data/raw/BOSSBase_1.01/cover")
OUTPUT = Path("data/manifests/covers.csv")

EXPECTED_COUNT = 10000
EXPECTED_SIZE = (512, 512)
EXPECTED_MODE = "L"


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


files = sorted(DATA_DIR.glob("*.pgm"))

print(f"PGM files found: {len(files)}")

records = []
errors = []

for path in tqdm(files, desc="Auditing BOSSBase"):
    try:
        with Image.open(path) as img:
            img.load()

            width, height = img.size
            mode = img.mode
            fmt = img.format

        records.append({
            "sample_id": f"cover_{path.stem}",
            "cover_id": path.stem,
            "path": path.as_posix(),
            "label": 0,
            "algorithm": "COVER",
            "payload": 0.0,
            "sha256": sha256_file(path),
            "width": width,
            "height": height,
            "mode": mode,
            "format": fmt,
        })

    except Exception as exc:
        errors.append((str(path), str(exc)))


df = pd.DataFrame(records)

# ------------------------------------------------------------
# Content-aware grouping
#
# Files with identical SHA-256 represent identical cover
# content and MUST remain in the same CV fold.
# The smallest numeric cover_id in each SHA-256 group becomes
# the canonical group_id.
# ------------------------------------------------------------

if not df.empty:
    df["cover_id_num"] = pd.to_numeric(df["cover_id"], errors="raise")

    canonical_groups = (
        df.groupby("sha256")["cover_id_num"]
        .transform("min")
        .astype(str)
    )

    df["group_id"] = canonical_groups
    df = df.drop(columns=["cover_id_num"])

    # Keep stable column order.
    columns = [
        "sample_id",
        "cover_id",
        "path",
        "label",
        "algorithm",
        "payload",
        "group_id",
        "sha256",
        "width",
        "height",
        "mode",
        "format",
    ]

    df = df[columns]


OUTPUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT, index=False)


print()
print("========== BOSSBase AUDIT ==========")
print("Expected files :", EXPECTED_COUNT)
print("Found files    :", len(files))
print("Readable files :", len(df))
print("Errors         :", len(errors))

if not df.empty:
    print("Image sizes    :", sorted(set(zip(df.width, df.height))))
    print("Image modes    :", sorted(df["mode"].unique()))
    print("Image formats  :", sorted(df["format"].unique()))
    print("Unique SHA256  :", df["sha256"].nunique())
    print("Unique IDs     :", df["cover_id"].nunique())
    print("Unique groups  :", df["group_id"].nunique())

    duplicate_rows = df[df.duplicated("sha256", keep=False)]

    if not duplicate_rows.empty:
        print()
        print("Identical-content files detected:")
        for sha256, group in duplicate_rows.groupby("sha256"):
            ids = sorted(group["cover_id"].tolist(), key=int)
            print(
                f"  group_id={group['group_id'].iloc[0]} "
                f"cover_ids={ids} "
                f"sha256={sha256}"
            )


valid = (
    len(files) == EXPECTED_COUNT
    and len(df) == EXPECTED_COUNT
    and len(errors) == 0
    and set(zip(df.width, df.height)) == {EXPECTED_SIZE}
    and set(df["mode"]) == {EXPECTED_MODE}
    and df["cover_id"].nunique() == EXPECTED_COUNT
)

print()

if valid:
    print("BOSSBase 1.01 structural audit: OK")

    if df["sha256"].nunique() < EXPECTED_COUNT:
        print(
            "NOTE: byte-identical covers exist and are "
            "protected by shared group_id."
        )

    print("BOSSBase 1.01 dataset status: READY")
else:
    print("BOSSBase 1.01 structural audit: FAILED")
    print("BOSSBase 1.01 dataset status: NOT READY")

    if errors:
        print()
        print("Errors:")
        for path, error in errors[:20]:
            print(path, error)

from pathlib import Path
import hashlib

import pandas as pd
from PIL import Image
from tqdm import tqdm


DATA_DIR = Path("data/raw/BOSSBase_1.01/cover")
OUTPUT = Path("data/manifests/covers.csv")

EXPECTED_COUNT = 10000
EXPECTED_SIZE = (512, 512)


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
            "group_id": path.stem,
            "sha256": sha256_file(path),
            "width": width,
            "height": height,
            "mode": mode,
            "format": fmt,
        })

    except Exception as exc:
        errors.append((str(path), str(exc)))


df = pd.DataFrame(records)

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

valid = (
    len(files) == EXPECTED_COUNT
    and len(df) == EXPECTED_COUNT
    and len(errors) == 0
    and set(zip(df.width, df.height)) == {EXPECTED_SIZE}
    and df["sha256"].nunique() == EXPECTED_COUNT
    and df["cover_id"].nunique() == EXPECTED_COUNT
)

print()

if valid:
    print("BOSSBase 1.01 audit: OK")
else:
    print("BOSSBase 1.01 audit: FAILED")

    if errors:
        print("\nErrors:")
        for path, error in errors[:20]:
            print(path, error)

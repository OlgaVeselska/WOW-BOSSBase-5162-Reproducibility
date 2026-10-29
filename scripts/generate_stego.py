import pandas as pd
from pathlib import Path
import sys
import argparse
import subprocess
import hashlib
import re
import numpy as np
from PIL import Image
# ============================================================
# BMHAT - stego dataset generation
# Stage 1: environment and path validation
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BOSSBASE_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "BOSSBase_1.01"
    / "cover"
)

WOW_EXE = (
    PROJECT_ROOT
    / "external"
    / "stego"
    / "WOW_windows_vc_2010_v10"
    / "executable"
    / "WOW.exe"
)
COVERS_MANIFEST = (
    PROJECT_ROOT
    / "data"
    / "manifests"
    / "covers.csv"
)
WOW_OUTPUT_01 = (
    PROJECT_ROOT
    / "data"
    / "stego"
    / "WOW"
    / "0.1"
)

WOW_OUTPUT_02 = (
    PROJECT_ROOT
    / "data"
    / "stego"
    / "WOW"
    / "0.2"
)
MANIFESTS_DIR = PROJECT_ROOT / "data" / "manifests"
STEGO_SEED_BASE = 20_260_000
WOW_VERSION = "WOW_windows_vc_2010_v10"
WOW_ARCHIVE_SHA256 = "B7986803FC1EBBD2070F27286F3D333198592ABD8F72B5B4E8FE3CF19B82193E"


def get_stego_seed(group_id: int) -> int:
    """
    Deterministic WOW embedding seed.

    Identical BOSSBase covers share group_id and therefore
    receive the same embedding seed.
    """
    seed = STEGO_SEED_BASE + int(group_id)

    if not (1 <= seed <= 2_147_483_647):
        raise ValueError(f"Invalid WOW int32 seed: {seed}")

    return seed

def sha256_file(path: Path) -> str:
    """Return SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_generation_manifest_path(payload: float) -> Path:
    """Return generation manifest path for the selected WOW payload."""
    payload_label = f"{payload:.1f}"
    return MANIFESTS_DIR / f"WOW_{payload_label}_generation.csv"


def save_generation_manifest_atomic(records: list[dict], manifest_path: Path) -> None:
    """Atomically save generation records to CSV."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = manifest_path.with_suffix(manifest_path.suffix + ".tmp")

    pd.DataFrame(records).to_csv(
        temp_path,
        index=False,
    )

    temp_path.replace(manifest_path)


def parse_wow_output(stdout: str, cover_id: int) -> tuple[float, float]:
    """Parse relative payload and distortion from WOW stdout."""
    pattern = rf"^{cover_id}\.pgm\s+\d+\s+\d+x\d+\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s*$"

    for line in stdout.splitlines():
        match = re.match(pattern, line.strip())
        if match:
            return float(match.group(1)), float(match.group(2))

    raise ValueError(f"Could not parse WOW output for cover_id={cover_id}")



def audit_stego_pixels(cover_path: Path, stego_path: Path) -> tuple[int, float, int, int]:
    """Compare cover and stego images and return pixel-change statistics."""
    cover = np.asarray(Image.open(cover_path), dtype=np.int16)
    stego = np.asarray(Image.open(stego_path), dtype=np.int16)

    if cover.shape != stego.shape:
        raise ValueError(f"Shape mismatch: cover={cover.shape}, stego={stego.shape}")

    delta = stego - cover
    changed_pixels = int(np.count_nonzero(delta))
    changed_pct = 100.0 * changed_pixels / delta.size
    min_delta = int(delta.min())
    max_delta = int(delta.max())

    if min_delta < -1 or max_delta > 1:
        raise ValueError(
            f"Unexpected WOW pixel changes: min_delta={min_delta}, max_delta={max_delta}"
        )

    return changed_pixels, changed_pct, min_delta, max_delta

def main():
    parser = argparse.ArgumentParser(
        description="BMHAT stego dataset generator"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show WOW commands without executing them."
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute WOW.exe and generate stego images."
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing stego images."
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume generation using only previously verified manifest records.",
    )
    parser.add_argument(
        "--payload",
        type=float,
        choices=[0.1, 0.2],
        default=0.1,
        help="WOW payload in bpp (0.1 or 0.2)."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N covers."
    )

    parser.add_argument(
        "--cover-id",
        type=int,
        default=None,
        help="Process only the specified cover_id."
    )

    args = parser.parse_args()

    if args.cover_id is not None and args.limit is not None:
        print("ERROR: --cover-id and --limit cannot be used together.")
        sys.exit(1)

    if args.dry_run and args.execute:
        parser.error("--dry-run and --execute cannot be used together.")

    if args.resume and args.overwrite:
        parser.error("--resume and --overwrite cannot be used together.")
    print("BMHAT stego generator")
    print("=" * 60)

    print(f"Project root : {PROJECT_ROOT}")
    print(f"BOSSBase     : {BOSSBASE_DIR}")
    print(f"WOW.exe      : {WOW_EXE}")
    print()

    # --------------------------------------------------------
    # Validate required inputs
    # --------------------------------------------------------

    if not BOSSBASE_DIR.is_dir():
        print("ERROR: BOSSBase directory not found.")
        sys.exit(1)

    if not WOW_EXE.is_file():
        print("ERROR: WOW.exe not found.")
        sys.exit(1)
    if not COVERS_MANIFEST.is_file():
        print("ERROR: covers.csv not found.")
        sys.exit(1)

    manifest = pd.read_csv(COVERS_MANIFEST)

    required_columns = {
        "cover_id",
        "group_id",
        "path",
        "sha256",
    }

    missing_columns = required_columns - set(manifest.columns)

    if missing_columns:
        print(
            "ERROR: Missing columns in covers.csv:",
            sorted(missing_columns),
        )
        sys.exit(1)

    manifest["stego_seed"] = (
        manifest["group_id"]
        .astype(int)
        .apply(get_stego_seed)
    )
    manifest = manifest.sort_values("cover_id", key=lambda s: s.astype(int)).reset_index(drop=True)

    if args.cover_id is not None:
        if args.cover_id < 1:
            print("ERROR: --cover-id must be >= 1.")
            sys.exit(1)

        manifest = manifest[
            manifest["cover_id"].astype(int) == int(args.cover_id)
        ].copy()

        if manifest.empty:
            print(f"ERROR: cover_id={args.cover_id} not found in covers manifest.")
            sys.exit(1)
    if args.limit is not None:
        if args.limit < 1:
            print("ERROR: --limit must be >= 1.")
            sys.exit(1)

        manifest = manifest.head(args.limit).copy()

    print(f"Selected      : {len(manifest)}")
    print(f"Payload       : {args.payload} bpp")
    print(f"Manifest rows : {len(manifest)}")
    print(f"Unique groups : {manifest['group_id'].nunique()}")
    print(f"Unique seeds  : {manifest['stego_seed'].nunique()}")
    covers = sorted(BOSSBASE_DIR.glob("*.pgm"))

    print(f"PGM covers   : {len(covers)}")

    if len(covers) != 10000:
        print("ERROR: Expected exactly 10000 BOSSBase PGM covers.")
        sys.exit(1)

    # --------------------------------------------------------
    # Prepare output directories
    # --------------------------------------------------------

    WOW_OUTPUT_01.mkdir(parents=True, exist_ok=True)
    WOW_OUTPUT_02.mkdir(parents=True, exist_ok=True)

    print(f"WOW 0.1 dir  : {WOW_OUTPUT_01}")
    print(f"WOW 0.2 dir  : {WOW_OUTPUT_02}")
    print()
    if args.dry_run:

        output_dir = (
            WOW_OUTPUT_01
            if args.payload == 0.1
            else WOW_OUTPUT_02
        )

        print()
        print("DRY RUN")
        print("=" * 60)





        for _, row in manifest.iterrows():

            cover_id = int(row["cover_id"])
            group_id = int(row["group_id"])
            stego_seed = int(row["stego_seed"])

            cover_path = BOSSBASE_DIR / f"{cover_id}.pgm"

            expected_cover_sha256 = str(row["sha256"]).lower()
            actual_cover_sha256 = sha256_file(cover_path).lower()

            if actual_cover_sha256 != expected_cover_sha256:
                print(f"ERROR: Cover SHA256 mismatch for cover_id={cover_id}")
                print(f"Expected: {expected_cover_sha256}")
                print(f"Actual  : {actual_cover_sha256}")
                sys.exit(1)
            output_path = output_dir / f"{cover_id}.pgm"


            command = [
                str(WOW_EXE),
                "-v",
                "-i", str(cover_path),
                "-O", str(output_dir),
                "-a", str(args.payload),
                "-p", "-1",
                "-w", "1",
                "-h", "0",
                "-r", str(stego_seed),
            ]

            print(f"cover_id   : {cover_id}")
            print(f"group_id   : {group_id}")
            print(f"stego_seed : {stego_seed}")
            print("Command:")
            print(" ".join(command))
            print("-" * 60)

        print("WOW.exe was NOT executed.")

    if args.execute:
        output_dir = WOW_OUTPUT_01 if args.payload == 0.1 else WOW_OUTPUT_02

        print()
        print("EXECUTE WOW")
        print("=" * 60)

        generation_records = []

        if args.resume or args.overwrite:
            generation_manifest_path = get_generation_manifest_path(args.payload)

            if not generation_manifest_path.is_file():
                if args.resume:
                    print(f"ERROR: Resume manifest not found: {generation_manifest_path}")
                    sys.exit(1)

                # --overwrite without an existing manifest starts from an empty manifest.
                print(f"Overwrite manifest not found; starting new manifest: {generation_manifest_path}")
                existing_manifest = None
            else:
                existing_manifest = pd.read_csv(generation_manifest_path)

            if existing_manifest is not None:
                required_resume_columns = {
                    "cover_id",
                    "group_id",
                    "algorithm",
                    "payload",
                    "stego_seed",
                    "cover_sha256",
                    "stego_sha256",
                    "changed_pixels",
                    "changed_pct",
                    "min_delta",
                    "max_delta",
                    "rel_payload",
                    "rel_distortion",
                    "output_path",
                    "generator_version",
                    "generator_archive_sha256",
                    "status",
                }
    
                missing_columns = required_resume_columns - set(existing_manifest.columns)
                if missing_columns:
                    print(
                        "ERROR: Resume manifest is missing required columns: "
                        + ", ".join(sorted(missing_columns))
                    )
                    sys.exit(1)
                if existing_manifest["cover_id"].duplicated().any():
                    duplicate_ids = sorted(
                        existing_manifest.loc[
                            existing_manifest["cover_id"].duplicated(keep=False),
                            "cover_id",
                        ].astype(int).unique().tolist()
                    )
                    print(
                        "ERROR: Resume manifest contains duplicate cover_id values: "
                        + ", ".join(map(str, duplicate_ids))
                    )
                    sys.exit(1)
    
                generation_records = existing_manifest.to_dict("records")
    
                existing_records_by_cover_id = {
                    int(record["cover_id"]): record
                    for record in generation_records
                }
    
                manifest_mode = "Resume" if args.resume else "Overwrite"
                print(f"{manifest_mode} manifest : {generation_manifest_path}")
                print(f"Existing records: {len(generation_records)}")

        for _, row in manifest.iterrows():
            cover_id = int(row["cover_id"])
            group_id = int(row["group_id"])
            stego_seed = int(row["stego_seed"])
            cover_path = BOSSBASE_DIR / f"{cover_id}.pgm"

            expected_cover_sha256 = str(row["sha256"]).lower()
            actual_cover_sha256 = sha256_file(cover_path).lower()

            if actual_cover_sha256 != expected_cover_sha256:
                print(f"ERROR: Cover SHA256 mismatch for cover_id={cover_id}")
                print(f"Expected: {expected_cover_sha256}")
                print(f"Actual  : {actual_cover_sha256}")
                sys.exit(1)

            output_path = output_dir / f"{cover_id}.pgm"

            if (
                args.resume
                and cover_id in existing_records_by_cover_id
                and not output_path.exists()
            ):
                print(
                    f"ERROR: Resume manifest record exists but stego file is missing: "
                    f"cover_id={cover_id}"
                )
                print(f"Expected file: {output_path}")
                sys.exit(1)

            if output_path.exists():
                if args.resume:
                    if cover_id not in existing_records_by_cover_id:
                        print(
                            f"ERROR: Existing stego file has no resume manifest record: "
                            f"cover_id={cover_id}"
                        )
                        print(f"File: {output_path}")
                        sys.exit(1)

                    resume_record = existing_records_by_cover_id[cover_id]

                    metadata_ok = (
                        int(resume_record["group_id"]) == group_id
                        and str(resume_record["algorithm"]).upper() == "WOW"
                        and abs(float(resume_record["payload"]) - float(args.payload)) < 1e-12
                        and int(resume_record["stego_seed"]) == stego_seed
                    )

                    if not metadata_ok:
                        print(f"ERROR: Resume metadata mismatch for cover_id={cover_id}")
                        sys.exit(1)

                    provenance_ok = (
                        str(resume_record["status"]).upper() == "OK"
                        and str(resume_record["generator_version"]) == WOW_VERSION
                        and str(resume_record["generator_archive_sha256"]).upper() == WOW_ARCHIVE_SHA256.upper()
                    )

                    if not provenance_ok:
                        print(f"ERROR: Resume provenance mismatch for cover_id={cover_id}")
                        sys.exit(1)

                    recorded_cover_sha256 = str(resume_record["cover_sha256"]).lower()
                    recorded_stego_sha256 = str(resume_record["stego_sha256"]).lower()
                    actual_stego_sha256 = sha256_file(output_path).lower()

                    if recorded_cover_sha256 != actual_cover_sha256:
                        print(f"ERROR: Resume cover SHA256 mismatch for cover_id={cover_id}")
                        print(f"Recorded: {recorded_cover_sha256}")
                        print(f"Actual  : {actual_cover_sha256}")
                        sys.exit(1)

                    if recorded_stego_sha256 != actual_stego_sha256:
                        print(f"ERROR: Resume stego SHA256 mismatch for cover_id={cover_id}")
                        print(f"Recorded: {recorded_stego_sha256}")
                        print(f"Actual  : {actual_stego_sha256}")
                        sys.exit(1)

                    try:
                        resume_changed_pixels, resume_changed_pct, resume_min_delta, resume_max_delta = audit_stego_pixels(
                            cover_path,
                            output_path,
                        )
                    except Exception as exc:
                        print(f"ERROR: Resume pixel audit failed for cover_id={cover_id}: {exc}")
                        sys.exit(1)

                    pixel_audit_ok = (
                        int(resume_record["changed_pixels"]) == resume_changed_pixels
                        and abs(float(resume_record["changed_pct"]) - resume_changed_pct) < 1e-9
                        and int(resume_record["min_delta"]) == resume_min_delta
                        and int(resume_record["max_delta"]) == resume_max_delta
                    )

                    if not pixel_audit_ok:
                        print(f"ERROR: Resume pixel statistics mismatch for cover_id={cover_id}")
                        sys.exit(1)

                    print(
                        f"RESUME OK: cover_id={cover_id} already verified; "
                        "skipping generation."
                    )
                    continue


                elif not args.overwrite:
                    print(f"ERROR: Output already exists: {output_path}")
                    print("Use --overwrite to replace existing stego files.")
                    sys.exit(1)

            command = [
                str(WOW_EXE),
                "-v",
                "-i", str(cover_path),
                "-O", str(output_dir),
                "-a", str(args.payload),
                "-p", "-1",
                "-w", "1",
                "-h", "0",
                "-r", str(stego_seed),
            ]

            print(f"Generating cover_id={cover_id}, group_id={group_id}, seed={stego_seed}")

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.stdout:
                print(result.stdout.strip())

            if result.returncode != 0:
                print(result.stderr.strip())
                print(f"ERROR: WOW failed for cover_id={cover_id}")
                sys.exit(result.returncode)

            rel_payload, rel_distortion = parse_wow_output(result.stdout, cover_id)
            print(f"Parsed rel_payload={rel_payload}, rel_distortion={rel_distortion}")

            output_path = output_dir / f"{cover_id}.pgm"
            if not output_path.is_file():
                print(f"ERROR: Output file was not created: {output_path}")
                sys.exit(1)

            changed_pixels, changed_pct, min_delta, max_delta = audit_stego_pixels(
                cover_path, output_path
            )

            print(
                f"Pixel audit: changed={changed_pixels}, "
                f"changed_pct={changed_pct:.6f}%, "
                f"delta=[{min_delta}, {max_delta}]"
            )

            cover_sha256 = sha256_file(cover_path)
            stego_sha256 = sha256_file(output_path)

            print(f"Cover SHA256: {cover_sha256}")
            print(f"Stego SHA256: {stego_sha256}")

            generation_record = {
                "cover_id": cover_id,
                "group_id": group_id,
                "algorithm": "WOW",
                "payload": float(args.payload),
                "stego_seed": stego_seed,
                "cover_sha256": cover_sha256,
                "stego_sha256": stego_sha256,
                "changed_pixels": changed_pixels,
                "changed_pct": changed_pct,
                "min_delta": min_delta,
                "max_delta": max_delta,
                "rel_payload": rel_payload,
                "rel_distortion": rel_distortion,
                "output_path": str(output_path),
                "generator_version": WOW_VERSION,
                "generator_archive_sha256": WOW_ARCHIVE_SHA256,
                "status": "OK",
            }

            # Upsert: replace an existing record for this cover_id,
            # otherwise append a new record.
            generation_records = [
                record
                for record in generation_records
                if int(record["cover_id"]) != cover_id
            ]
            generation_records.append(generation_record)
            generation_records.sort(key=lambda record: int(record["cover_id"]))

            generation_manifest_path = get_generation_manifest_path(args.payload)
            save_generation_manifest_atomic(
                generation_records,
                generation_manifest_path,
            )

            print(f"OK: {output_path}")
            print("-" * 60)


        print(f"Generation manifest: {generation_manifest_path}")
        print(f"Generation records : {len(generation_records)}")

        print("WOW generation completed.")
    print("Path validation: OK")
    if not args.execute:
        print("No stego images generated in this stage.")


if __name__ == "__main__":
    main()




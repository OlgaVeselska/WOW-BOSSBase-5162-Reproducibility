# WOW / BOSSBase 1.01 image 5162 — reproducibility materials (DRAFT)

Research companion materials for the analysis of finite wet-cost clipping in WOW steganography on BOSSBase 1.01 image `5162.pgm`.

**Status: pre-publication draft. Exact local regeneration verified, but not independently reproducible from this ZIP alone.** The BOSSBase cover and generated stego images, original WOW executable/source and some project manifests are not included. The archived Python scripts are preserved unchanged, and currently assume the original BMHAT project directory structure.

## Contents
- `scripts/diagnose_wow_5162.py`: cost and lambda diagnostics for image 5162.
- `scripts/audit_wow_capacity.py`: dataset-level cost-state audit using `conseal`; the reported `max_bpp_hard` is a *combinatorial proxy under hard-exclusion interpretation*, **not** demonstrated WOW embedding capacity.
- `scripts/generate_stego.py`: BMHAT dataset generation script, not a self-contained 5162 reproduction command.
- `scripts/verify_bossbase.py`, `scripts/verify_bossbase_v1.py`: source-dataset verification utilities.
- `results/WOW_capacity_audit.csv`: dataset-wide audit (10,000 rows).
- `results/WOW_5162_analiza_ladunku.csv`: 16 modeled payload settings; semicolon-delimited.
- `metadata/WOW_code_verification.txt`, `metadata/WOW_embedding_details.txt`: excerpts from implementation inspection.

## Selected audited facts (image 5162)
- Image size: 512 x 512 pixels; 254,773 zeros (97.1882%).
- 245,972 pixels assigned the finite wet-cost threshold `W = 1e10` in the audited cost-state analysis.
- Combinatorial hard-exclusion proxy: `0.07813933789373644` bpp; **do not interpret as actual embedding capacity**.
- The analysis distinguishes finite costs from truly forbidden transitions. A finite `W` may still lead to nonzero model probability.

## Dependencies and inputs
The scripts reference paths such as `data/raw/BOSSBase_1.01/cover/5162.pgm`, `data/manifests/`, and `external/stego/WOW_windows_vc_2010_v10/`. These must be supplied in a local copy of the BMHAT directory tree. Python packages used include NumPy, SciPy, Pillow, pandas, tqdm, and `conseal` (depending on the script). Exact package versions have not yet been verified.

**Verified local reproduction:** the experimenter regenerated `5162.pgm` with `WOW.exe -v -i <cover> -O <output_dir> -a 0.2 -p -1 -w 1 -h 0 -r 20265162`; original and regenerated stego files have matching SHA-256 `FC377F6957BF643BC04B96AFF7325416171A3691C89E163644BD2D888243E6D8`. WOW executable SHA-256: `7C547CA838C5BE1C3D89D0BD52F50E4F17C41A476AB61A3C510E433F8809AC41`. See `metadata/REPRODUCTION_5162.md`. This archive is not standalone: BOSSBase cover and the executable must be obtained separately.

## Pending before public release
1. DONE: verify WOW invocation, seed and simulation mode by byte-identical local regeneration.
2. Record environment and dependency versions, and add executable commands and expected outputs.
3. Test scripts from a fresh checkout with licensed BOSSBase data.
4. Review rights for third-party code, data, and output redistribution.
5. Add a license for original scripts only after author approval.
6. Add DOI/repository URL once actually published.

## Data availability
BOSSBase images are not included. Obtain them through their legitimate distribution channel and comply with their terms. This draft includes derived numeric audit outputs only.

## Pre-release verification and interpretation

See [`metadata/VALIDATION_REPORT.md`](metadata/VALIDATION_REPORT.md) for checked file integrity, remaining blockers, and the important distinction between the modeled CSV lambda and the separate C++-logic diagnostic.

### Run in the original BMHAT environment (Windows PowerShell)

The original scripts are archived *without edits*. Their expected working directory is the BMHAT project root, not this ZIP's root. After restoring the authorized BOSSBase dataset, WOW executable and relevant project manifests into their original locations:

```powershell
cd C:\Users\ovese\BMHAT
python scripts\diagnose_wow_5162.py
python scripts\generate_stego.py --dry-run --cover-id 5162 --payload 0.2
```

The second command only previews a *proposed* WOW invocation; it does not establish that the existing image `5162.pgm` was generated using those settings. Do not use `--execute` until output paths, input hashes, and configuration are checked.

A syntax-only check on this repository's scripts can be performed without images:

```powershell
python -m compileall -q scripts
```

**Interpretation note:** `results/WOW_5162_analiza_ladunku.csv` uses semicolon-separated fields and comma decimal notation. At 0.20 bpp it records a modeled lambda of `4.862298064178816e-10` (200 iterations), which must not be substituted for the distinct C++-logic diagnostic result.


## Independently verified cover–stego comparison (image 5162)

The script `scripts/compare_cover_stego.py` computes pixelwise differences directly
from the original 8-bit grayscale cover and the generated 0.2-bpp WOW stego image.
The original images are **not redistributed**; supply locally obtained files.

```powershell
python -m pip install numpy Pillow
python scripts/compare_cover_stego.py --cover "C:\Users\ovese\BMHAT\data\raw\BOSSBase_1.01\cover\5162.pgm" --stego "C:\Users\ovese\BMHAT\data\stego\WOW\0.2\5162.pgm"
```

The verified metrics are saved in `results/WOW_5162_cover_stego_pixel_comparison.csv`.
The reported `zero_to_255` count is an **observed pixel transition**, not by itself
proof of the generating program's arithmetic mechanism.

SHA-256 (cover): `c7b1bf90db3896b1a08610b01d61239148c2e110fc9b54dd0627da4718804efb`

SHA-256 (stego): `fc377f6957bf643bc04b96aff7325416171a3691c89e163644bd2d888243e6d8`

**Provenance limitation:** The original random seed, embedding mode (simulation
versus STC), and invocation used to produce the stego image have not been
independently established from a generation log. The comparison reproduces
the observed pixel counts, not the original embedding process.


## Verified deterministic reproduction of image 5162

The experimenter reproduced the WOW stego image **byte-for-byte** using seed `20265162`, simulated embedding (`-h 0`), and payload argument `-a 0.2`. The original and regenerated files share SHA-256 `FC377F6957BF643BC04B96AFF7325416171A3691C89E163644BD2D888243E6D8`. See [`metadata/REPRODUCTION_5162.md`](metadata/REPRODUCTION_5162.md) for the exact PowerShell command, original console output, and limitations.

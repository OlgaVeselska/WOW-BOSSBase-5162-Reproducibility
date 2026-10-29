# WOW / BOSSBase 1.01 Image 5162 — Reproducibility Materials

Research companion materials for the analysis of finite wet-cost clipping in WOW steganography, focusing on the extreme case of image `5162.pgm` from BOSSBase 1.01.

**Status: Public research companion package.** A controlled local rerun of the WOW executable reproduced the original stego image byte-for-byte using seed `20265162`, simulated embedding (`-h 0`), and a requested payload of `0.2` bpp. File identity was verified using SHA-256 checksums.

The repository provides diagnostic scripts, numerical results, experimental documentation, and reproduction instructions. It is not a fully self-contained reproduction environment: BOSSBase images, the WOW executable, and certain original project dependencies must be obtained separately.

## 1. Repository contents

### Scripts

- `scripts/diagnose_wow_5162.py`: cost and lambda diagnostics for image 5162.
- `scripts/audit_wow_capacity.py`: dataset-level cost-state audit using `conseal`. The reported `max_bpp_hard` is a combinatorial proxy under a hard-exclusion interpretation, **not an experimentally demonstrated WOW embedding capacity**.
- `scripts/generate_stego.py`: BMHAT dataset-generation utility, not a standalone reproduction script for image 5162.
- `scripts/compare_cover_stego.py`: pixelwise comparison between the original cover and generated stego image.
- `scripts/verify_bossbase.py`, `scripts/verify_bossbase_v1.py`: BOSSBase dataset-verification utilities.

### Numerical results

- `results/WOW_capacity_audit.csv`: dataset-wide cost-state audit covering 10,000 images.
- `results/WOW_5162_analiza_ladunku.csv`: modeled results for 16 payload settings; semicolon-delimited.
- `results/WOW_5162_cover_stego_pixel_comparison.csv`: verified pixel-transition statistics.

### Experimental documentation

- `metadata/REPRODUCTION_5162.md`: deterministic reproduction command, parameters, console output, SHA-256 verification, and limitations.
- `metadata/VALIDATION_REPORT.md`: validation findings and remaining reproducibility limitations.
- `metadata/WOW_code_verification.txt`, `metadata/WOW_embedding_details.txt`: excerpts from implementation inspection.

## 2. Selected audited facts (image 5162)

The cost-state audit identified the following characteristics:

- Image dimensions: **512 × 512 pixels**.
- Zero-valued pixels: **254,773 (97.1882%)**.
- Pixels assigned the finite wet-cost threshold `W = 1e10`: **245,972**.
- Combinatorial hard-exclusion proxy: **0.07813933789373644 bpp**.

**Important interpretation:** The hard-exclusion proxy is not the actual embedding capacity of WOW. The analysis distinguishes finite modification costs from strictly forbidden transitions. A finite wet cost may still yield a nonzero modification probability.

## 3. Dependencies and input data

The original scripts reference directories such as:

- `data/raw/BOSSBase_1.01/cover/`
- `data/manifests/`
- `external/stego/WOW_windows_vc_2010_v10/`

The scripts were preserved without modifications and assume the original BMHAT project structure.

Depending on the script, Python dependencies include NumPy, SciPy, Pillow, pandas, tqdm, and `conseal`.

Exact package versions have not yet been independently verified.

Researchers must obtain the BOSSBase 1.01 dataset and the corresponding WOW implementation through authorized sources.

### WOW executable verification

The executable used for the successful local reproduction has the following SHA-256 checksum:

`7C547CA838C5BE1C3D89D0BD52F50E4F17C41A476AB61A3C510E433F8809AC41`

This checksum identifies the executable used in the verified experiment. Its human-readable version metadata and cross-machine reproducibility have not yet been established.

## 4. Verification and interpretation

See [`metadata/VALIDATION_REPORT.md`](metadata/VALIDATION_REPORT.md) for validation details, integrity checks, and remaining limitations.

### Running diagnostic scripts (Windows PowerShell)

The scripts are intended to be executed from the BMHAT project root after restoring the required dataset, executable, and project manifests.

**Note:** Replace the example Windows paths with the corresponding paths in your local BMHAT environment.

```powershell
cd C:\Users\ovese\BMHAT

python scripts\diagnose_wow_5162.py

python scripts\generate_stego.py --dry-run --cover-id 5162 --payload 0.2
```

The second command performs a dry run and previews the proposed WOW invocation without generating an image. The deterministic reproduction described in Section 6 was established by a separate, controlled execution of the WOW executable.

Before executing any generation script, verify the input files, output paths, and configuration to avoid overwriting existing results.

A syntax-only check of the repository scripts can be performed without image data:

```powershell
python -m compileall -q scripts
```

### Interpretation of lambda values

The file `results/WOW_5162_analiza_ladunku.csv` uses semicolon-separated fields and comma decimal notation.

At a modeled payload of `0.20` bpp, it reports:

- Modeled lambda: `4.862298064178816e-10`.
- Iterations: `200`.

This value must not be confused with the separate C++-logic diagnostic, which produced:

- Lambda: `4.856701707467437e-10`.
- Calculated relative payload (`alpha_out`): `0.20055906474590302`.
- Iterations: `40`.

These results originate from distinct numerical procedures and should not be treated as interchangeable.

## 5. Independently verified cover–stego comparison (image 5162)

The script `scripts/compare_cover_stego.py` performs a pixelwise comparison between the original 8-bit grayscale BOSSBase 1.01 cover image (`5162.pgm`) and the corresponding WOW stego image generated with a requested payload of `0.2` bpp.

The analysis quantifies pixel modifications, including transitions from intensity 0 to 255, which are relevant to the investigation of finite wet-cost clipping.

### Execution instructions (Windows PowerShell)

The original cover and generated stego images must be available locally. The comparison script is intended to be executed from the BMHAT project root.

**Note:** Replace the example Windows paths with the corresponding paths in your local BMHAT environment.

```powershell
cd C:\Users\ovese\BMHAT

python -m pip install numpy Pillow

python scripts/compare_cover_stego.py --cover "C:\Users\ovese\BMHAT\data\raw\BOSSBase_1.01\cover\5162.pgm" --stego "C:\Users\ovese\BMHAT\data\stego\WOW\0.2\5162.pgm"
```

### Verified results

The pixel-comparison statistics are provided in:

`results/WOW_5162_cover_stego_pixel_comparison.csv`

The analysis confirmed:

| Metric | Value |
|---|---:|
| Image dimensions | 512 × 512 |
| Modified pixels | 13,010 |
| Unchanged pixels | 249,134 |
| Transitions from intensity 0 to 255 | 1,936 |

The observed `zero_to_255` transitions are directly measured pixel changes. They do not, by themselves, establish the precise arithmetic mechanism responsible for these transitions.

### SHA-256 verification

**Original cover image:**

`c7b1bf90db3896b1a08610b01d61239148c2e110fc9b54dd0627da4718804efb`

**WOW stego image (requested payload 0.2 bpp):**

`fc377f6957bf643bc04b96aff7325416171a3691c89e163644bd2d888243e6d8`

These checksums enable verification of the exact input and output files used in the experiment.

## 6. Verified deterministic reproduction of image 5162

A controlled rerun of the WOW Windows executable was performed using the following configuration:

| Parameter | Value |
|---|---|
| Cover image | `5162.pgm` |
| Image dimensions | 512 × 512 |
| Requested payload | `0.2` bpp |
| Random seed | `20265162` |
| Embedding mode | Simulated embedding (`-h 0`) |
| Payload argument | `-a 0.2` |
| Additional arguments | `-p -1 -w 1` |

### Reproduction command (Windows PowerShell)

Run the following commands from the original BMHAT project root:

```powershell
New-Item -ItemType Directory -Force "results\wow_5162_reproduction" | Out-Null

& "external\stego\WOW_windows_vc_2010_v10\executable\WOW.exe" `
  -v `
  -i "data\raw\BOSSBase_1.01\cover\5162.pgm" `
  -O "results\wow_5162_reproduction" `
  -a 0.2 `
  -p -1 `
  -w 1 `
  -h 0 `
  -r 20265162
```

### Observed executable output

```text
# WOW DISTORTION EMBEDDING SIMULATOR
# output directory = results\wow_5162_reproduction
# running payload-limited sender with alpha = 0.2
# simulating embedding as if the best coding scheme is available
#file name     seed            size          rel. payload     rel. distortion
5162.pgm       20265162        512x512       0.201116         1.43674e+008
Time elapsed: 1.133 s
```

The executable reported a relative payload of `0.201116`, which is distinct from the requested value of `0.2` bpp.

### Byte-for-byte reproduction

The original and regenerated stego images have the same SHA-256 checksum:

`FC377F6957BF643BC04B96AFF7325416171A3691C89E163644BD2D888243E6D8`

This establishes byte-for-byte reproduction of the original stego file under the verified local configuration.

### Provenance and limitations

The original generation log was not retained. Nevertheless, a controlled rerun using the documented configuration reproduced the original stego image byte-for-byte.

The experiment used simulated embedding (`-h 0`), not actual syndrome-trellis coding (STC).

The confirmed reproduction applies to the specified executable and local environment. Independent reproduction on a different machine has not yet been demonstrated.

Further details are provided in [`metadata/REPRODUCTION_5162.md`](metadata/REPRODUCTION_5162.md).

## 7. Data availability

The repository is publicly available at:

https://github.com/OlgaVeselska/WOW-BOSSBase-5162-Reproducibility

It contains diagnostic scripts, numerical audit results, pixel-comparison statistics, and experimental documentation.

BOSSBase cover and stego images, the original WOW executable, and third-party source code are **not redistributed**.

Researchers must obtain the necessary external resources independently and comply with their respective licensing and distribution conditions.

No DOI has been assigned to this repository.

## 8. Remaining reproducibility and documentation tasks

1. Record the exact Python environment and dependency versions.
2. Test the scripts from a fresh repository checkout using legitimately obtained BOSSBase data.
3. Review redistribution rights for third-party code and derived outputs.
4. Add an appropriate license for original scripts after author approval.

The controlled local reproduction of image 5162 has been completed and verified using SHA-256 checksums.

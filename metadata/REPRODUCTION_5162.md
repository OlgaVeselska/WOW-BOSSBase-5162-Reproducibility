# Verified deterministic reproduction: WOW / BOSSBase 5162

## Evidence

On 2026-10-29, the experimenter ran the WOW Windows executable against the local BOSSBase 1.01 cover `5162.pgm` (512 x 512) with a fresh output directory. The resulting stego PGM was byte-identical to the previously generated WOW 0.2-bpp stego file, verified by SHA-256.

### Command (PowerShell; run from the BMHAT project root)

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

### WOW executable output (reported by experimenter)

```text
# WOW DISTORTION EMBEDDING SIMULATOR
# output directory = results\wow_5162_reproduction
# running payload-limited sender with alpha = 0.2
# simulating embedding as if the best coding scheme is available
#file name     seed            size          rel. payload     rel. distortion
5162.pgm       20265162        512x512       0.201116         1.43674e+008
Time elapsed: 1.133 s
```

### File identity

Both original `data\stego\WOW\0.2\5162.pgm` and regenerated `results\wow_5162_reproduction\5162.pgm`:

```text
SHA-256: FC377F6957BF643BC04B96AFF7325416171A3691C89E163644BD2D888243E6D8
```

### Scope and limitations

- This confirms exact reproduction of the specific stego file with the specified WOW executable and arguments, on the experimenter's local system.
- `-h 0` corresponds to simulated embedding, not STC coding. `-r 20265162` is the confirmed seed.
- The WOW executable reports a relative payload of `0.201116`, distinct from the requested `0.2` bpp; retain both values as reported.
- The C++ lambda diagnostic (lambda `4.856701707467437e-10`, alpha_out `0.20055906474590302`, 40 iterations) is a separate diagnostic calculation. Do not conflate its `alpha_out` with the executable's reported relative payload.
- This package does not redistribute BOSSBase cover/stego images or the WOW binary. A user must obtain them separately under applicable licenses and preserve the same executable implementation for exact reproduction.
- The WOW Windows executable used for the successful reproduction has SHA-256 `7C547CA838C5BE1C3D89D0BD52F50E4F17C41A476AB61A3C510E433F8809AC41` (reported by the experimenter using PowerShell `Get-FileHash`). Its human-readable version metadata and cross-machine reproducibility have not been independently established.

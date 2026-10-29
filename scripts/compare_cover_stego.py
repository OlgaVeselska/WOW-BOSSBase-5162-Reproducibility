#!/usr/bin/env python3
"""Reproduce the pixelwise cover/stego comparison for BOSSBase image 5162.
Requires: numpy, Pillow. No BOSSBase images are redistributed.
"""
import argparse
import csv
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image


def load(path):
    arr = np.asarray(Image.open(path))
    if arr.ndim != 2 or arr.dtype != np.uint8:
        raise ValueError(f"Expected 8-bit grayscale PGM: {path}")
    return arr.astype(np.int16)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cover", type=Path, required=True)
    p.add_argument("--stego", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    a, b = load(args.cover), load(args.stego)
    if a.shape != b.shape:
        raise ValueError("Cover and stego dimensions differ")
    delta = b - a  # signed arithmetic avoids uint8 overflow
    counts = {
        "pixels_total": int(a.size),
        "pixels_unchanged": int(np.count_nonzero(delta == 0)),
        "pixels_changed": int(np.count_nonzero(delta != 0)),
        "delta_plus_1": int(np.count_nonzero(delta == 1)),
        "delta_minus_1": int(np.count_nonzero(delta == -1)),
        "zero_to_255": int(np.count_nonzero((a == 0) & (b == 255))),
        "cover_zero_pixels": int(np.count_nonzero(a == 0)),
        "cover_sha256": sha256(args.cover),
        "stego_sha256": sha256(args.stego),
    }
    for k, v in counts.items():
        print(f"{k}: {v}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["metric", "value"])
            w.writerows(counts.items())


if __name__ == "__main__":
    main()

from pathlib import Path

import numpy as np
import pandas as pd
import conseal
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COVER_DIR = PROJECT_ROOT / "data" / "raw" / "BOSSBase_1.01" / "cover"
OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "manifests"
    / "WOW_capacity_audit.csv"
)

WET_COST = 1e10


def calculate_capacity(path):
    x = np.array(Image.open(path), dtype=np.uint8)

    rho_p1, rho_m1 = conseal.wow.compute_cost_adjusted(
        x0=x,
        p=-1,
        wet_cost=WET_COST,
    )

    # Diagnostic interpretation only:
    # costs equal to wetCost are treated as unavailable states.
    allow_p1 = np.logical_and(
        rho_p1 < WET_COST,
        x < 255,
    )
    allow_m1 = np.logical_and(
        rho_m1 < WET_COST,
        x > 0,
    )

    states = (
        1
        + allow_p1.astype(np.int8)
        + allow_m1.astype(np.int8)
    )

    max_bits = float(
        np.sum(
            np.log2(
                states.astype(np.float64)
            )
        )
    )

    n_pixels = int(x.size)
    max_bpp_hard = max_bits / n_pixels

    return {
        "min_pixel": int(x.min()),
        "max_pixel": int(x.max()),
        "zero_pixels": int(np.sum(x == 0)),
        "zero_pct": float(np.mean(x == 0) * 100.0),
        "one_state_pixels": int(np.sum(states == 1)),
        "two_state_pixels": int(np.sum(states == 2)),
        "three_state_pixels": int(np.sum(states == 3)),
        "max_bits_hard": max_bits,
        "max_bpp_hard": max_bpp_hard,
        "feasible_0.1": bool(max_bpp_hard >= 0.1),
        "feasible_0.2": bool(max_bpp_hard >= 0.2),
    }


def main():
    files = sorted(
        COVER_DIR.glob("*.pgm"),
        key=lambda p: int(p.stem),
    )

    if len(files) != 10000:
        raise RuntimeError(
            f"Expected 10000 BOSSBase covers, found {len(files)}"
        )

    rows = []

    print("WOW hard-wet-cost diagnostic audit")
    print(f"Covers: {len(files)}")
    print(f"wetCost: {WET_COST:.0e}")
    print()

    for i, path in enumerate(files, start=1):
        result = calculate_capacity(path)

        rows.append(
            {
                "cover_id": int(path.stem),
                **result,
            }
        )

        if i % 100 == 0 or i == len(files):
            print(
                f"\rProcessed {i:5d}/{len(files)}",
                end="",
                flush=True,
            )

    print()

    df = pd.DataFrame(rows)
    df = df.sort_values("cover_id").reset_index(drop=True)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    below_01 = df.loc[
        ~df["feasible_0.1"],
        "cover_id",
    ].tolist()

    below_02 = df.loc[
        ~df["feasible_0.2"],
        "cover_id",
    ].tolist()

    minimum_row = df.loc[
        df["max_bpp_hard"].idxmin()
    ]

    print()
    print("=== SUMMARY ===")
    print(f"Rows: {len(df)}")
    print(
        "Minimum max_bpp_hard:",
        f"{df['max_bpp_hard'].min():.6f}",
    )
    print(
        "Median max_bpp_hard:",
        f"{df['max_bpp_hard'].median():.6f}",
    )
    print(
        "Mean max_bpp_hard:",
        f"{df['max_bpp_hard'].mean():.6f}",
    )
    print(
        "Covers below 0.1 bpp:",
        len(below_01),
    )
    print(
        "Covers below 0.2 bpp:",
        len(below_02),
    )
    print(
        "Lowest-capacity cover:",
        int(minimum_row["cover_id"]),
    )
    print(
        "Lowest capacity:",
        f"{minimum_row['max_bpp_hard']:.6f}",
    )

    print()
    print("Cover IDs below 0.1 bpp:")
    print(below_01)

    print()
    print("Cover IDs below 0.2 bpp:")
    print(below_02)

    print()
    print("Saved:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
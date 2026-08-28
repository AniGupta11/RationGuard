#!/usr/bin/env python3
"""
Rename commodity columns in rationguard_dataset.csv to align with app naming.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def main():
    csv_path = Path("data/raw/rationguard_dataset.csv")
    if not csv_path.exists():
        raise SystemExit(f"Dataset not found at {csv_path}")

    df = pd.read_csv(csv_path)

    # Convert previously renamed columns back to the dataset's canonical names.
    rename_pairs = {
        "SunflowerOil": "SoyabeanOil",
        "MustardOil": "PalmOil",
        "UradDal": "Masoor",
        "ToorDal": "Moong",
        "ChanaDal": "Chana",
    }
    rename_map = {}

    for src, dest in rename_pairs.items():
        for suffix in ("_Entitled", "_Claimed"):
            old = f"{src}{suffix}"
            new = f"{dest}{suffix}"
            if old in df.columns:
                rename_map[old] = new

    if not rename_map:
        print("No matching columns found to rename.")
        return

    df.rename(columns=rename_map, inplace=True)
    df.to_csv(csv_path, index=False)

    print("Renamed columns:", rename_map)


if __name__ == "__main__":
    main()


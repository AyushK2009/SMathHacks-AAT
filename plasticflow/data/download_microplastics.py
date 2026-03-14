"""
Attempt to download NOAA NCEI Marine Microplastics data.
Falls back to synthetic data generation on any failure.
"""

import os
import sys
import requests
import pandas as pd

NOAA_URL = "https://www.ncei.noaa.gov/data/oceans/microplastics/microplastics.csv"
OUT_DIR = os.path.join(os.path.dirname(__file__), "processed")
OUT_PATH = os.path.join(OUT_DIR, "microplastics.csv")

REQUIRED_COLS = {"latitude", "longitude", "density"}


def download_noaa(url: str, dest: str, timeout: int = 30) -> bool:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(response.content)
        # Validate it looks like microplastics data
        df = pd.read_csv(dest, nrows=5)
        if not REQUIRED_COLS.issubset(set(col.lower() for col in df.columns)):
            print(f"WARNING: Downloaded file missing expected columns. Got: {list(df.columns)}")
            return False
        return True
    except Exception as e:
        print(f"WARNING: NOAA download failed — {e}")
        return False


def fallback_synthetic():
    print("WARNING: Falling back to synthetic microplastics data.")
    script_dir = os.path.dirname(__file__)
    sys.path.insert(0, script_dir)
    from generate_synthetic_data import generate_synthetic_data
    df = generate_synthetic_data(n_obs=500)
    os.makedirs(OUT_DIR, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Synthetic data saved to {OUT_PATH}")


if __name__ == "__main__":
    print(f"Attempting to download NOAA microplastics data from:\n  {NOAA_URL}")
    success = download_noaa(NOAA_URL, OUT_PATH)
    if success:
        df = pd.read_csv(OUT_PATH)
        print(f"Downloaded {len(df)} real observations to {OUT_PATH}")
    else:
        fallback_synthetic()

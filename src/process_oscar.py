"""Lazy loader for OSCAR ocean surface current NetCDF files.

Provides `load_oscar()` for downstream code and a CLI inspection mode.
"""

import os
import glob
from pathlib import Path

import xarray as xr

# Resolve the OSCAR data directory relative to the repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _REPO_ROOT / "data" / "OSCAR_L4_OC_FINAL_V2.0_2.0-20260314_215516"


def load_oscar(data_dir: os.PathLike | str | None = None) -> xr.Dataset:
    """Return a lazily-loaded xarray Dataset of all daily OSCAR files.

    Parameters
    ----------
    data_dir : path, optional
        Override the default OSCAR data directory.

    Returns
    -------
    xr.Dataset
        Lazily-loaded dataset (backed by dask arrays).
    """
    data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
    pattern = str(data_dir / "oscar_currents_final_*.nc")
    files = sorted(glob.glob(pattern))

    if not files:
        raise FileNotFoundError(f"No files matching {pattern}")

    # Filter out corrupt / duplicate-download files
    valid_files: list[str] = []
    for f in files:
        if " " in Path(f).name or "(1)" in Path(f).name:
            continue
        try:
            xr.open_dataset(f, engine="netcdf4").close()
            valid_files.append(f)
        except (OSError, ValueError):
            continue

    if not valid_files:
        raise FileNotFoundError("All NetCDF files are corrupt or invalid")

    return xr.open_mfdataset(valid_files, combine="by_coords", chunks="auto")


if __name__ == "__main__":
    ds = load_oscar()
    print(f"Found {len(ds.time)} time steps")
    print(f"\n=== Dataset Info ===")
    print(f"Dimensions:  {dict(ds.sizes)}")
    print(f"Coordinates: {list(ds.coords)}")
    print(f"Variables:   {list(ds.data_vars)}")
    if "time" in ds.coords:
        print(f"Time range:  {ds.time.values[0]} → {ds.time.values[-1]}")
    print(f"\nFull summary:\n{ds}")

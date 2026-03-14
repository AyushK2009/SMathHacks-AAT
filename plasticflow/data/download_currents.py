"""
Attempt to download OSCAR monthly climatology NetCDF.
Falls back to a synthetic current field using:
  u = 0.1 * cos(lat * pi/30)
  v = 0.05 * sin(lon * pi/60)
on a 1° global grid.
"""

import os
import numpy as np
import requests

OUT_DIR = os.path.join(os.path.dirname(__file__), "processed")
OUT_PATH = os.path.join(OUT_DIR, "currents.nc")

# OSCAR is distributed via PO.DAAC; direct anonymous download requires Earthdata login.
# We attempt a known public endpoint; any failure triggers synthetic fallback.
OSCAR_URL = (
    "https://podaac-opendap.jpl.nasa.gov/opendap/allData/oscar/preview/L4/"
    "oscar_third_deg/oscar_vel2021.nc.gz"
)


def generate_synthetic_currents(path: str):
    """Generate synthetic current field and save as NetCDF."""
    try:
        import netCDF4 as nc
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "netCDF4", "-q"])
        import netCDF4 as nc

    lats = np.arange(-89.5, 90.5, 1.0)
    lons = np.arange(-179.5, 180.5, 1.0)

    lon2d, lat2d = np.meshgrid(lons, lats)
    u = 0.1 * np.cos(lat2d * np.pi / 30)
    v = 0.05 * np.sin(lon2d * np.pi / 60)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with nc.Dataset(path, "w", format="NETCDF4") as ds:
        ds.title = "Synthetic ocean surface currents (PlasticFlow fallback)"

        ds.createDimension("lat", len(lats))
        ds.createDimension("lon", len(lons))

        lat_var = ds.createVariable("lat", "f4", ("lat",))
        lat_var.units = "degrees_north"
        lat_var[:] = lats

        lon_var = ds.createVariable("lon", "f4", ("lon",))
        lon_var.units = "degrees_east"
        lon_var[:] = lons

        u_var = ds.createVariable("u", "f4", ("lat", "lon"), fill_value=np.nan)
        u_var.units = "m/s"
        u_var.long_name = "Eastward surface current"
        u_var[:] = u.astype("f4")

        v_var = ds.createVariable("v", "f4", ("lat", "lon"), fill_value=np.nan)
        v_var.units = "m/s"
        v_var.long_name = "Northward surface current"
        v_var[:] = v.astype("f4")

    print(f"Synthetic current field saved to {path}")


def download_oscar(url: str, dest: str, timeout: int = 60) -> bool:
    try:
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"WARNING: OSCAR download failed — {e}")
        return False


if __name__ == "__main__":
    print(f"Attempting to download OSCAR currents from:\n  {OSCAR_URL}")
    success = download_oscar(OSCAR_URL, OUT_PATH)
    if not success:
        print("WARNING: Falling back to synthetic current field.")
        generate_synthetic_currents(OUT_PATH)
    else:
        print(f"OSCAR currents saved to {OUT_PATH}")

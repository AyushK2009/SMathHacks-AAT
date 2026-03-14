"""
Core Lagrangian particle advection engine.
Euler forward scheme, vectorized across all particles simultaneously.
"""

import os
import warnings
import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator

# Approximate bounding boxes [lat_min, lat_max, lon_min, lon_max] for major landmasses
# Used for a simple (fast) land mask — not pixel-perfect but sufficient for ocean drift
LAND_BOXES = [
    # North America
    (24, 72, -168, -52),
    # South America
    (-56, 12, -82, -34),
    # Europe
    (36, 71, -10, 40),
    # Africa
    (-35, 37, -18, 52),
    # Asia (main)
    (0, 77, 25, 150),
    # Australia
    (-44, -10, 113, 154),
    # Greenland
    (59, 84, -74, -11),
    # Antarctica (handled via lat boundary)
]

DEG_PER_METER_LAT = 1.0 / 111320.0  # meters per degree latitude (constant)


def _deg_per_meter_lon(lat_deg: np.ndarray) -> np.ndarray:
    """Degrees longitude per meter at given latitudes."""
    return 1.0 / (111320.0 * np.cos(np.radians(lat_deg)) + 1e-10)


def _is_land(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """
    Returns boolean mask: True where particle is on land or outside bounds.
    Uses rectangular bounding boxes for major landmasses.
    """
    on_land = np.zeros(len(lats), dtype=bool)

    # Ice / polar boundaries
    on_land |= (lats > 75) | (lats < -78)

    for lat_min, lat_max, lon_min, lon_max in LAND_BOXES:
        in_box = (
            (lats >= lat_min) & (lats <= lat_max) &
            (lons >= lon_min) & (lons <= lon_max)
        )
        on_land |= in_box

    return on_land


def _synthetic_uv(lats: np.ndarray, lons: np.ndarray):
    """Fallback current field formula from CLAUDE.md."""
    u = 0.1 * np.cos(lats * np.pi / 30)
    v = 0.05 * np.sin(lons * np.pi / 60)
    return u, v


class ParticleSimulator:
    """
    Lagrangian particle simulator using Euler forward advection.
    All particle operations are fully vectorized with numpy.
    """

    def __init__(self):
        self._u_interp = None
        self._v_interp = None
        self._use_synthetic = True

    def load_current_field(self, path: str):
        """
        Load NetCDF u/v current fields and build RegularGridInterpolator.
        Falls back to synthetic field if file is missing or unreadable.
        """
        if not os.path.exists(path):
            warnings.warn(
                f"Current field not found at {path}. Using synthetic fallback.",
                RuntimeWarning,
            )
            self._use_synthetic = True
            return

        try:
            import xarray as xr

            ds = xr.open_dataset(path)

            # Normalize coordinate names
            lat_names = ["lat", "latitude", "y"]
            lon_names = ["lon", "longitude", "x"]
            u_names = ["u", "U", "uo", "eastward_sea_water_velocity"]
            v_names = ["v", "V", "vo", "northward_sea_water_velocity"]

            lat_key = next((k for k in lat_names if k in ds), None)
            lon_key = next((k for k in lon_names if k in ds), None)
            u_key = next((k for k in u_names if k in ds), None)
            v_key = next((k for k in v_names if k in ds), None)

            if not all([lat_key, lon_key, u_key, v_key]):
                raise ValueError(
                    f"Could not find required variables. Keys: {list(ds.data_vars)}"
                )

            lats = ds[lat_key].values.astype(float)
            lons = ds[lon_key].values.astype(float)

            u_data = ds[u_key].values
            v_data = ds[v_key].values

            # Handle time/depth dimensions — take first slice
            while u_data.ndim > 2:
                u_data = u_data[0]
            while v_data.ndim > 2:
                v_data = v_data[0]

            u_data = np.nan_to_num(u_data.astype(float), nan=0.0)
            v_data = np.nan_to_num(v_data.astype(float), nan=0.0)

            # Ensure lat is ascending for RegularGridInterpolator
            if lats[0] > lats[-1]:
                lats = lats[::-1]
                u_data = u_data[::-1, :]
                v_data = v_data[::-1, :]

            self._u_interp = RegularGridInterpolator(
                (lats, lons), u_data, method="linear", bounds_error=False, fill_value=0.0
            )
            self._v_interp = RegularGridInterpolator(
                (lats, lons), v_data, method="linear", bounds_error=False, fill_value=0.0
            )
            self._use_synthetic = False
            print(f"Loaded current field from {path} ({len(lats)}x{len(lons)} grid)")

        except Exception as e:
            warnings.warn(
                f"Failed to load current field: {e}. Using synthetic fallback.",
                RuntimeWarning,
            )
            self._use_synthetic = True

    def interpolate_uv(self, lats: np.ndarray, lons: np.ndarray):
        """
        Vectorized bilinear interpolation of u, v across all particles simultaneously.
        Returns (u, v) arrays in m/s.
        """
        if self._use_synthetic:
            return _synthetic_uv(lats, lons)

        points = np.column_stack([lats, lons])
        u = self._u_interp(points)
        v = self._v_interp(points)
        return u, v

    def step(
        self,
        lats: np.ndarray,
        lons: np.ndarray,
        active: np.ndarray,
        dt: float = 86400.0,
    ):
        """
        Single vectorized Euler forward step.
        - Converts m/s to degrees using local scale factors
        - Applies land mask: particles that hit land are frozen in place
        Returns updated (lats, lons, active).
        """
        if not np.any(active):
            return lats, lons, active

        u, v = self.interpolate_uv(lats, lons)

        # Convert displacement from meters to degrees
        dlat = v * dt * DEG_PER_METER_LAT
        dlon = u * dt * _deg_per_meter_lon(lats)

        new_lats = lats.copy()
        new_lons = lons.copy()
        new_lats[active] += dlat[active]
        new_lons[active] += dlon[active]

        # Wrap longitude to [-180, 180]
        new_lons = ((new_lons + 180) % 360) - 180

        # Clamp latitude
        new_lats = np.clip(new_lats, -89.9, 89.9)

        # Land mask: freeze particles that land on land
        hit_land = _is_land(new_lats, new_lons)
        still_active = active & ~hit_land

        # Apply: only update particles that are active and didn't hit land
        moved = active & ~hit_land
        lats[moved] = new_lats[moved]
        lons[moved] = new_lons[moved]

        return lats, lons, still_active

    def run(
        self,
        release_lats: np.ndarray,
        release_lons: np.ndarray,
        city: str = "unknown",
        days: int = 1825,
        record_every: int = 1,
    ) -> pd.DataFrame:
        """
        Run full simulation for one release group.
        Returns DataFrame: particle_id, city, day, lat, lon
        """
        n_particles = len(release_lats)
        lats = release_lats.copy().astype(float)
        lons = release_lons.copy().astype(float)
        active = ~_is_land(lats, lons)

        records = []
        for day in range(0, days + 1, record_every):
            if day > 0:
                for _ in range(record_every):
                    lats, lons, active = self.step(lats, lons, active)

            records.append(
                pd.DataFrame({
                    "particle_id": np.arange(n_particles),
                    "city": city,
                    "day": day,
                    "lat": lats.copy(),
                    "lon": lons.copy(),
                    "active": active.copy(),
                })
            )

        return pd.concat(records, ignore_index=True)

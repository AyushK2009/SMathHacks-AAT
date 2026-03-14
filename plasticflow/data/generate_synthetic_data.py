"""
Generate realistic synthetic microplastics observation data.
500 observations across 5 ocean basins with realistic distributions.
"""

import numpy as np
import pandas as pd
import os

OCEAN_BASINS = {
    "North Pacific": {
        "lat": (10, 60),
        "lon": (140, 240),
        "weight": 0.30,
    },
    "South Pacific": {
        "lat": (-55, 10),
        "lon": (150, 290),
        "weight": 0.15,
    },
    "North Atlantic": {
        "lat": (10, 65),
        "lon": (280, 360),
        "weight": 0.30,
    },
    "South Atlantic": {
        "lat": (-55, 10),
        "lon": (320, 360),
        "weight": 0.10,
    },
    "Indian Ocean": {
        "lat": (-40, 25),
        "lon": (45, 100),
        "weight": 0.15,
    },
}

SAMPLING_METHODS = ["Manta trawl", "Neuston net", "Water column", "Sediment core", "Beach survey"]
YEARS = list(range(2010, 2024))


def generate_synthetic_data(n_obs=500, seed=42):
    np.random.seed(seed)
    records = []

    weights = [b["weight"] for b in OCEAN_BASINS.values()]
    basin_names = list(OCEAN_BASINS.keys())
    basin_counts = np.round(np.array(weights) * n_obs).astype(int)
    # Adjust rounding drift
    basin_counts[-1] += n_obs - basin_counts.sum()

    for basin, count in zip(basin_names, basin_counts):
        info = OCEAN_BASINS[basin]
        lat_min, lat_max = info["lat"]
        lon_min, lon_max = info["lon"]

        lats = np.random.uniform(lat_min, lat_max, count)
        # Convert lon > 180 back to negative
        lons_raw = np.random.uniform(lon_min, lon_max, count)
        lons = np.where(lons_raw > 180, lons_raw - 360, lons_raw)

        # Log-normal density: higher near gyres / shipping lanes
        # Bias density higher toward subtropical latitudes (garbage patches ~30°)
        lat_factor = np.exp(-0.5 * ((np.abs(lats) - 30) / 20) ** 2)
        mu = -1.5 + lat_factor * 1.5  # log-space mean
        sigma = 1.2
        densities = np.random.lognormal(mu, sigma, count)
        densities = np.clip(densities, 0.001, 500.0)

        methods = np.random.choice(SAMPLING_METHODS, count)
        years = np.random.choice(YEARS, count)

        for i in range(count):
            records.append({
                "latitude": round(lats[i], 4),
                "longitude": round(lons[i], 4),
                "density": round(densities[i], 4),
                "ocean_basin": basin,
                "sampling_method": methods[i],
                "year": int(years[i]),
            })

    df = pd.DataFrame(records)

    # Density class labels
    bins = [0, 0.01, 0.1, 1.0, 10.0, float("inf")]
    labels = ["Very Low", "Low", "Medium", "High", "Very High"]
    df["density_class"] = pd.cut(df["density"], bins=bins, labels=labels)

    return df


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "processed")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "microplastics.csv")

    df = generate_synthetic_data(n_obs=500)
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} synthetic observations to {out_path}")
    print(df.groupby("ocean_basin")["density"].describe().round(3))

"""
Precompute 5-year particle trajectories for all 10 cities.
Saves:
  results/simulation_results/trajectories.parquet
  results/simulation_results/final_positions.parquet

Must be run before launching the Streamlit app.
"""

import os
import sys
import numpy as np
import pandas as pd

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.simulate import ParticleSimulator

CITIES = {
    "Shanghai":       (31.2,  121.5),
    "Mumbai":         (19.1,   72.9),
    "Lagos":          ( 6.5,    3.4),
    "New York":       (40.7,  -74.0),
    "São Paulo":      (-23.9, -46.3),
    "Jakarta":        (-6.1,  106.8),
    "Dhaka":          (22.3,   91.8),
    "Manila":         (14.6,  121.0),
    "Cairo":          (31.2,   29.9),
    "Los Angeles":    (33.7, -118.2),
}

N_PARTICLES = 500
DAYS = 1825          # 5 years
RECORD_EVERY = 5     # Record every 5 days to keep parquet manageable

CURRENTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "processed", "currents.nc"
)
RESULTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "results", "simulation_results"
)


def release_particles(center_lat: float, center_lon: float, n: int = N_PARTICLES, seed: int = 0):
    """Release N particles scattered ±0.5° around city center."""
    rng = np.random.default_rng(seed)
    lats = center_lat + rng.uniform(-0.5, 0.5, n)
    lons = center_lon + rng.uniform(-0.5, 0.5, n)
    return lats, lons


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    sim = ParticleSimulator()
    sim.load_current_field(CURRENTS_PATH)

    all_trajectories = []
    all_final = []

    for i, (city, (clat, clon)) in enumerate(CITIES.items(), 1):
        print(f"[{i}/{len(CITIES)}] Simulating {city} ({N_PARTICLES} particles, {DAYS} days)...")
        lats, lons = release_particles(clat, clon, N_PARTICLES, seed=i)
        traj = sim.run(lats, lons, city=city, days=DAYS, record_every=RECORD_EVERY)
        all_trajectories.append(traj)

        final = traj[traj["day"] == traj["day"].max()].copy()
        all_final.append(final)
        print(f"    Done. {len(traj)} trajectory records.")

    print("\nSaving trajectories...")
    traj_df = pd.concat(all_trajectories, ignore_index=True)
    traj_path = os.path.join(RESULTS_DIR, "trajectories.parquet")
    traj_df.to_parquet(traj_path, index=False)
    print(f"Saved {len(traj_df):,} rows to {traj_path}")

    print("Saving final positions...")
    final_df = pd.concat(all_final, ignore_index=True)
    final_path = os.path.join(RESULTS_DIR, "final_positions.parquet")
    final_df.to_parquet(final_path, index=False)
    print(f"Saved {len(final_df):,} rows to {final_path}")

    print("\nPrecomputation complete.")


if __name__ == "__main__":
    main()

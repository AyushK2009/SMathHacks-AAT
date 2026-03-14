"""
Shipping lane proximity analysis.
Generates synthetic shipping lane density raster and computes
Spearman correlation with microplastics density.
Saves scatter plot to results/figures/shipping_correlation.png
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "microplastics.csv")
FIG_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "figures")

# Major shipping lane centroids: (lat_center, lon_center, label)
SHIPPING_LANES = [
    # Trans-Pacific (lat 30-40N, lon 120E-120W)
    (35.0,  175.0, "Trans-Pacific"),
    (35.0,  210.0, "Trans-Pacific"),
    (35.0,  240.0, "Trans-Pacific"),
    # Trans-Atlantic (lat 35-45N, lon 280-360 / -80 to 0)
    (40.0, -60.0,  "Trans-Atlantic"),
    (40.0, -30.0,  "Trans-Atlantic"),
    (40.0,  -5.0,  "Trans-Atlantic"),
    # Indian Ocean (lat 0-20N, lon 60-100E)
    (10.0,  65.0,  "Indian Ocean"),
    (10.0,  80.0,  "Indian Ocean"),
    (10.0,  95.0,  "Indian Ocean"),
]


def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.lower().strip() for c in df.columns]
    return df


def nearest_lane_distance(lat: float, lon: float) -> float:
    """Euclidean distance (degrees) to the nearest shipping lane centroid."""
    min_dist = float("inf")
    for slat, slon, _ in SHIPPING_LANES:
        # Adjust lon for antimeridian
        dlat = lat - slat
        dlon = lon - slon
        # Wrap lon difference to [-180, 180]
        dlon = (dlon + 180) % 360 - 180
        dist = np.sqrt(dlat**2 + dlon**2)
        if dist < min_dist:
            min_dist = dist
    return min_dist


def compute_proximity(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["shipping_proximity"] = df.apply(
        lambda row: nearest_lane_distance(row["latitude"], row["longitude"]),
        axis=1,
    )
    # Invert: higher value = closer to shipping lane
    max_dist = df["shipping_proximity"].max()
    df["shipping_proximity_inv"] = max_dist - df["shipping_proximity"]
    return df


def plot_correlation(df: pd.DataFrame, r: float, p: float, out_path: str):
    fig, ax = plt.subplots(figsize=(8, 6))

    sc = ax.scatter(
        df["shipping_proximity_inv"],
        df["density"],
        c=df["density"],
        cmap="plasma",
        alpha=0.5,
        s=15,
        norm=matplotlib.colors.LogNorm(
            vmin=max(df["density"].min(), 1e-4),
            vmax=df["density"].max(),
        ),
    )
    plt.colorbar(sc, ax=ax, label="Density (particles/m³)")

    # Trend line
    z = np.polyfit(df["shipping_proximity_inv"], np.log1p(df["density"]), 1)
    x_line = np.linspace(df["shipping_proximity_inv"].min(), df["shipping_proximity_inv"].max(), 100)
    y_line = np.expm1(np.polyval(z, x_line))
    ax.plot(x_line, y_line, "r--", linewidth=1.5, label="Trend (log-linear)")

    ax.set_xlabel("Shipping Proximity (inverted distance, degrees)", fontsize=11)
    ax.set_ylabel("Microplastics Density (particles/m³)", fontsize=11)
    ax.set_yscale("log")
    ax.set_title("Microplastics Density vs. Shipping Lane Proximity", fontsize=13, fontweight="bold")
    ax.annotate(
        f"Spearman r = {r:.3f}\np = {p:.2e}",
        xy=(0.05, 0.92), xycoords="axes fraction",
        fontsize=11, color="darkred",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", edgecolor="gray"),
    )
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved: {out_path}")


def main():
    os.makedirs(FIG_DIR, exist_ok=True)

    df = load_data(DATA_PATH)
    print(f"Loaded {len(df)} observations")

    df = compute_proximity(df)

    r, p = spearmanr(df["density"], df["shipping_proximity_inv"])
    print(f"\nSpearman r (density vs. shipping proximity): r={r:.4f}, p={p:.4e}")
    print("Interpretation: positive r means higher density near shipping lanes.")

    plot_correlation(df, r, p, os.path.join(FIG_DIR, "shipping_correlation.png"))
    print("\nCorrelation analysis complete.")


if __name__ == "__main__":
    main()

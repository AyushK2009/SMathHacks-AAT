"""
Exploratory data analysis for microplastics observations.
Generates 3 figures saved to results/figures/.
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
from scipy.stats import spearmanr

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "microplastics.csv")
FIG_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "figures")


def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Normalize column names
    df.columns = [c.lower().strip() for c in df.columns]
    return df


def stats_by_basin(df: pd.DataFrame) -> pd.DataFrame:
    stats = df.groupby("ocean_basin")["density"].agg(["median", "mean", "count"]).round(4)
    print("\nDensity by Ocean Basin:")
    print(stats.to_string())
    return stats


def stats_by_year(df: pd.DataFrame) -> pd.Series:
    counts = df.groupby("year").size().rename("count")
    print("\nObservation count by year:")
    print(counts.to_string())
    return counts


def run_dbscan_hotspots(df: pd.DataFrame, eps: float = 2.0, min_samples: int = 5, top_n: int = 10):
    """DBSCAN spatial clustering on high-density observations."""
    # Use top 50% by density as "high density"
    threshold = df["density"].quantile(0.5)
    high = df[df["density"] >= threshold].copy()

    coords = high[["latitude", "longitude"]].values
    db = DBSCAN(eps=eps, min_samples=min_samples, metric="euclidean").fit(coords)
    high["cluster"] = db.labels_

    # Find cluster centroids (exclude noise label -1)
    clusters = high[high["cluster"] >= 0].copy()
    if len(clusters) == 0:
        print("No DBSCAN clusters found.")
        return pd.DataFrame()

    centroids = (
        clusters.groupby("cluster")[["latitude", "longitude", "density"]]
        .agg({"latitude": "mean", "longitude": "mean", "density": "median"})
        .sort_values("density", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    print(f"\nTop {len(centroids)} hotspot clusters (DBSCAN eps={eps}, min_samples={min_samples}):")
    print(centroids.to_string())
    return centroids


def spearman_density_latitude(df: pd.DataFrame):
    """Spearman correlation between density and |latitude| as shipping lane proxy."""
    r, p = spearmanr(df["density"], df["latitude"].abs())
    print(f"\nSpearman r (density vs |latitude|): r={r:.4f}, p={p:.4e}")
    return r, p


def plot_density_by_basin(stats: pd.DataFrame, out_path: str):
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(stats)))
    bars = ax.bar(stats.index, stats["median"], color=colors, edgecolor="white", linewidth=0.8)
    ax.set_xlabel("Ocean Basin", fontsize=12)
    ax.set_ylabel("Median Density (particles/m³)", fontsize=12)
    ax.set_title("Microplastics Density by Ocean Basin", fontsize=14, fontweight="bold")
    ax.tick_params(axis="x", rotation=20)
    for bar, val in zip(bars, stats["median"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.02,
                f"{val:.3f}", ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved: {out_path}")


def plot_observations_by_year(counts: pd.Series, out_path: str):
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(counts.index, counts.values, marker="o", color="#1f77b4", linewidth=2, markersize=6)
    ax.fill_between(counts.index, counts.values, alpha=0.15, color="#1f77b4")
    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel("Number of Observations", fontsize=12)
    ax.set_title("Microplastics Observations by Year", fontsize=14, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved: {out_path}")


def plot_spatial_clusters(df: pd.DataFrame, centroids: pd.DataFrame, out_path: str):
    fig, ax = plt.subplots(figsize=(12, 6))

    sc = ax.scatter(
        df["longitude"], df["latitude"],
        c=np.log1p(df["density"]), cmap="plasma",
        s=10, alpha=0.5, label="Observations"
    )
    plt.colorbar(sc, ax=ax, label="log(density + 1)")

    if len(centroids) > 0:
        ax.scatter(
            centroids["longitude"], centroids["latitude"],
            marker="*", s=200, color="red", edgecolors="white",
            linewidth=0.5, zorder=5, label="Hotspot centroids"
        )

    ax.set_xlabel("Longitude", fontsize=12)
    ax.set_ylabel("Latitude", fontsize=12)
    ax.set_title("Spatial Distribution & DBSCAN Hotspots", fontsize=14, fontweight="bold")
    ax.legend(loc="upper right")
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved: {out_path}")


def main():
    os.makedirs(FIG_DIR, exist_ok=True)

    df = load_data(DATA_PATH)
    print(f"Loaded {len(df)} observations")

    basin_stats = stats_by_basin(df)
    year_counts = stats_by_year(df)
    centroids = run_dbscan_hotspots(df)
    spearman_density_latitude(df)

    plot_density_by_basin(basin_stats, os.path.join(FIG_DIR, "density_by_basin.png"))
    plot_observations_by_year(year_counts, os.path.join(FIG_DIR, "observations_by_year.png"))
    plot_spatial_clusters(df, centroids, os.path.join(FIG_DIR, "spatial_clusters.png"))

    print("\nEDA complete.")


if __name__ == "__main__":
    main()

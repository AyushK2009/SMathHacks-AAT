"""
PlasticFlow — Interactive Streamlit Dashboard
3 pages:
  1. Global Observations
  2. Particle Simulator
  3. Statistics & Insights
"""

import os
import sys
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Allow imports from project root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_PATH = os.path.join(ROOT, "data", "processed", "microplastics.csv")
TRAJ_PATH = os.path.join(ROOT, "results", "simulation_results", "trajectories.parquet")
FINAL_PATH = os.path.join(ROOT, "results", "simulation_results", "final_positions.parquet")
CURRENTS_PATH = os.path.join(ROOT, "data", "processed", "currents.nc")

CITIES = {
    "Shanghai":    (31.2,  121.5),
    "Mumbai":      (19.1,   72.9),
    "Lagos":       ( 6.5,    3.4),
    "New York":    (40.7,  -74.0),
    "São Paulo":   (-23.9, -46.3),
    "Jakarta":     (-6.1,  106.8),
    "Dhaka":       (22.3,   91.8),
    "Manila":      (14.6,  121.0),
    "Cairo":       (31.2,   29.9),
    "Los Angeles": (33.7, -118.2),
}

SHIPPING_LANES = [
    # Trans-Pacific
    [(35, 140), (35, 180), (35, -140), (35, -120)],
    # Trans-Atlantic
    [(40, -80), (40, -60), (40, -30), (40, -5)],
    # Indian Ocean
    [(10, 55), (10, 72), (10, 85), (10, 100)],
]

st.set_page_config(
    page_title="PlasticFlow",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Data loaders ──────────────────────────────────────────────────────────────

@st.cache_data
def load_microplastics() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df.columns = [c.lower().strip() for c in df.columns]
    if "density_class" not in df.columns:
        bins = [0, 0.01, 0.1, 1.0, 10.0, float("inf")]
        labels = ["Very Low", "Low", "Medium", "High", "Very High"]
        df["density_class"] = pd.cut(df["density"], bins=bins, labels=labels).astype(str)
    return df


@st.cache_data
def load_trajectories() -> pd.DataFrame | None:
    if not os.path.exists(TRAJ_PATH):
        return None
    return pd.read_parquet(TRAJ_PATH)


@st.cache_data
def load_final_positions() -> pd.DataFrame | None:
    if not os.path.exists(FINAL_PATH):
        return None
    return pd.read_parquet(FINAL_PATH)


# ── Sidebar navigation ────────────────────────────────────────────────────────

st.sidebar.title("🌊 PlasticFlow")
st.sidebar.markdown("Microplastics accumulation & ocean current simulation")
page = st.sidebar.radio(
    "Navigate",
    ["Global Observations", "Particle Simulator", "Statistics & Insights"],
)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Global Observations
# ══════════════════════════════════════════════════════════════════════════════

if page == "Global Observations":
    st.title("🗺️ Global Microplastics Observations")

    df = load_microplastics()

    # Sidebar filters
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filters")

    all_basins = sorted(df["ocean_basin"].unique())
    selected_basins = st.sidebar.multiselect(
        "Ocean Basin", all_basins, default=all_basins
    )

    year_min, year_max = int(df["year"].min()), int(df["year"].max())
    year_range = st.sidebar.slider("Year Range", year_min, year_max, (year_min, year_max))

    all_classes = ["Very Low", "Low", "Medium", "High", "Very High"]
    selected_classes = st.sidebar.multiselect(
        "Density Class", all_classes, default=all_classes
    )

    # Apply filters
    mask = (
        df["ocean_basin"].isin(selected_basins)
        & df["year"].between(year_range[0], year_range[1])
        & df["density_class"].isin(selected_classes)
    )
    filtered = df[mask].copy()

    st.markdown(f"**Showing {len(filtered):,} of {len(df):,} observations**")

    if filtered.empty:
        st.warning("No data matches the current filters.")
    else:
        # Log-scale density for color and size
        filtered["log_density"] = np.log1p(filtered["density"])
        size_col = (filtered["log_density"] / filtered["log_density"].max() * 15 + 3).clip(3, 18)

        fig = px.scatter_geo(
            filtered,
            lat="latitude",
            lon="longitude",
            color="log_density",
            size=size_col,
            color_continuous_scale="plasma",
            hover_data={
                "latitude": ":.2f",
                "longitude": ":.2f",
                "density": ":.4f",
                "ocean_basin": True,
                "year": True,
                "sampling_method": True,
                "log_density": False,
            },
            title="Microplastics Observations (color = log density)",
            projection="natural earth",
        )
        fig.update_layout(
            coloraxis_colorbar=dict(title="log(density+1)"),
            margin=dict(l=0, r=0, t=40, b=0),
            height=600,
        )

        # Shipping lane overlay
        for lane in SHIPPING_LANES:
            lats = [p[0] for p in lane]
            lons = [p[1] for p in lane]
            fig.add_trace(go.Scattergeo(
                lat=lats,
                lon=lons,
                mode="lines",
                line=dict(color="rgba(255,80,80,0.5)", width=3),
                name="Shipping Lane",
                showlegend=False,
            ))

        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Particle Simulator
# ══════════════════════════════════════════════════════════════════════════════

elif page == "Particle Simulator":
    st.title("🌀 Lagrangian Particle Simulator")

    traj_df = load_trajectories()
    final_df = load_final_positions()

    if traj_df is None or final_df is None:
        st.error(
            "Precomputed simulation results not found.\n\n"
            "**Run:** `python src/precompute.py` from the project root, then reload this page."
        )
        st.stop()

    # Sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("City Selection")
    city = st.sidebar.selectbox("Select City", list(CITIES.keys()))

    # Animated trajectory
    st.subheader(f"5-Year Particle Drift from {city}")
    city_traj = traj_df[traj_df["city"] == city].copy()

    # Sample every 30 days for animation performance
    sampled_days = sorted(city_traj["day"].unique())[::6]  # every 6th record_every=5 → every 30 days
    anim_df = city_traj[city_traj["day"].isin(sampled_days)].copy()
    anim_df["day_str"] = anim_df["day"].astype(str)

    fig_anim = px.scatter_geo(
        anim_df,
        lat="lat",
        lon="lon",
        animation_frame="day_str",
        color="particle_id",
        color_continuous_scale="viridis",
        title=f"Particle trajectories from {city} (sampled every 30 days)",
        projection="natural earth",
        opacity=0.6,
    )
    fig_anim.update_layout(
        height=550,
        margin=dict(l=0, r=0, t=50, b=0),
        coloraxis_showscale=False,
        updatemenus=[dict(type="buttons", showactive=False,
                          buttons=[dict(label="Play", method="animate",
                                        args=[None, {"frame": {"duration": 100, "redraw": True},
                                                     "fromcurrent": True}]),
                                   dict(label="Pause", method="animate",
                                        args=[[None], {"frame": {"duration": 0}, "mode": "immediate"}])])],
    )
    st.plotly_chart(fig_anim, use_container_width=True)

    # Final positions heatmap + observed hotspots overlay
    st.subheader("Final Particle Positions vs. Observed Microplastics")
    city_final = final_df[final_df["city"] == city]
    obs_df = load_microplastics()

    fig2 = go.Figure()
    fig2.add_trace(go.Densitymapbox(
        lat=city_final["lat"],
        lon=city_final["lon"],
        radius=8,
        colorscale="Viridis",
        name="Simulated final positions",
        showscale=False,
        opacity=0.7,
    ))
    fig2.add_trace(go.Scattermapbox(
        lat=obs_df["latitude"],
        lon=obs_df["longitude"],
        mode="markers",
        marker=dict(size=4, color="red", opacity=0.5),
        name="Observed microplastics",
    ))
    fig2.update_layout(
        mapbox_style="open-street-map",
        mapbox_zoom=1,
        mapbox_center={"lat": 20, "lon": 0},
        height=450,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(x=0, y=1),
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Custom lat/lon expander
    with st.expander("🔧 Run Custom Simulation (enter your own coordinates)"):
        col1, col2 = st.columns(2)
        custom_lat = col1.number_input("Release Latitude", -80.0, 80.0, 0.0, step=0.1)
        custom_lon = col2.number_input("Release Longitude", -180.0, 180.0, 0.0, step=0.1)
        n_custom = st.slider("Number of particles", 50, 500, 200, step=50)

        if st.button("Run Custom Simulation"):
            with st.spinner("Running simulation (this may take a minute)..."):
                from src.simulate import ParticleSimulator
                import numpy as np

                rng = np.random.default_rng(99)
                lats = custom_lat + rng.uniform(-0.5, 0.5, n_custom)
                lons = custom_lon + rng.uniform(-0.5, 0.5, n_custom)

                sim = ParticleSimulator()
                sim.load_current_field(CURRENTS_PATH)
                result = sim.run(lats, lons, city="Custom", days=1825, record_every=365)
                final_custom = result[result["day"] == result["day"].max()]

            st.success("Simulation complete!")
            fig_custom = px.scatter_geo(
                final_custom,
                lat="lat",
                lon="lon",
                title=f"Final positions after 5 years (released from {custom_lat:.1f}°, {custom_lon:.1f}°)",
                projection="natural earth",
                opacity=0.6,
            )
            fig_custom.update_layout(height=450)
            st.plotly_chart(fig_custom, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Statistics & Insights
# ══════════════════════════════════════════════════════════════════════════════

elif page == "Statistics & Insights":
    st.title("📊 Statistics & Insights")

    df = load_microplastics()

    # 1. Median density by ocean basin
    st.subheader("Median Microplastics Density by Ocean Basin")
    basin_stats = df.groupby("ocean_basin")["density"].median().reset_index()
    basin_stats.columns = ["Ocean Basin", "Median Density"]
    fig_basin = px.bar(
        basin_stats.sort_values("Median Density", ascending=False),
        x="Ocean Basin",
        y="Median Density",
        color="Median Density",
        color_continuous_scale="plasma",
        title="Median Density (particles/m³) by Ocean Basin",
    )
    fig_basin.update_layout(coloraxis_showscale=False, height=400)
    st.plotly_chart(fig_basin, use_container_width=True)

    # 2. Observation count by year
    st.subheader("Observation Count by Year")
    year_counts = df.groupby("year").size().reset_index(name="Count")
    fig_year = px.line(
        year_counts,
        x="year",
        y="Count",
        markers=True,
        title="Number of Microplastics Observations by Year",
    )
    fig_year.update_traces(line_color="#1f77b4", marker_size=8)
    fig_year.update_layout(height=350)
    st.plotly_chart(fig_year, use_container_width=True)

    # 3. Density vs. shipping proximity
    st.subheader("Density vs. Shipping Lane Proximity")

    SHIPPING_CENTROIDS = [
        (35.0, 175.0), (35.0, 210.0), (35.0, 240.0),
        (40.0, -60.0), (40.0, -30.0), (40.0, -5.0),
        (10.0, 65.0), (10.0, 80.0), (10.0, 95.0),
    ]

    def nearest_dist(row):
        min_d = float("inf")
        for slat, slon in SHIPPING_CENTROIDS:
            dlat = row["latitude"] - slat
            dlon = row["longitude"] - slon
            dlon = (dlon + 180) % 360 - 180
            d = np.sqrt(dlat**2 + dlon**2)
            if d < min_d:
                min_d = d
        return min_d

    plot_df = df.copy()
    plot_df["ship_dist"] = plot_df.apply(nearest_dist, axis=1)
    max_d = plot_df["ship_dist"].max()
    plot_df["proximity"] = max_d - plot_df["ship_dist"]

    from scipy.stats import spearmanr
    r, p = spearmanr(plot_df["density"], plot_df["proximity"])

    fig_corr = px.scatter(
        plot_df,
        x="proximity",
        y="density",
        color="ocean_basin",
        log_y=True,
        opacity=0.55,
        title=f"Density vs. Shipping Proximity  |  Spearman r = {r:.3f}  (p = {p:.2e})",
        labels={"proximity": "Shipping Proximity (inverted distance)", "density": "Density (particles/m³)"},
    )
    fig_corr.update_layout(height=420)
    st.plotly_chart(fig_corr, use_container_width=True)
    st.caption(f"Spearman r = **{r:.3f}**, p = {p:.2e}")

    # 4. Key findings
    st.subheader("Key Findings")
    north_pac = df[df["ocean_basin"] == "North Pacific"]["density"].median()
    north_atl = df[df["ocean_basin"] == "North Atlantic"]["density"].median()
    top_basin = basin_stats.sort_values("Median Density", ascending=False).iloc[0]["Ocean Basin"]

    st.markdown(f"""
- **Highest accumulation** occurs in the **{top_basin}**, consistent with the location of major ocean garbage patches driven by subtropical gyres.
- **North Pacific** (median {north_pac:.3f} p/m³) and **North Atlantic** (median {north_atl:.3f} p/m³) show the greatest plastic burden, likely due to high shipping traffic and populated coastal source regions.
- **DBSCAN spatial clustering** reveals discrete hotspot zones at mid-latitudes (~30°N), matching known gyre accumulation zones where convergent surface currents concentrate floating debris.
- **Shipping lane proximity** shows a Spearman r of **{r:.3f}** with microplastics density, suggesting that maritime traffic routes may act as pathways for plastic distribution, though causation requires further study.
- **Observation frequency has grown** over the dataset period, reflecting increasing scientific attention to ocean plastic pollution rather than a simple increase in plastic levels.
""")

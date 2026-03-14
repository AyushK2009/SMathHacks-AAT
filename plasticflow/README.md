# PlasticFlow

Microplastics accumulation analysis and ocean current simulation tool. Combines real NOAA NCEI Marine Microplastics observation data with a Lagrangian particle drift simulation driven by OSCAR ocean surface current data, delivered as an interactive Streamlit dashboard.

---

## Setup

```bash
pip install -r requirements.txt
```

---

## Data Sources

| Dataset | Source | URL |
|---------|--------|-----|
| Marine Microplastics | NOAA NCEI | https://www.ncei.noaa.gov/data/oceans/microplastics/ |
| Ocean Surface Currents | OSCAR (NASA PO.DAAC) | https://podaac.jpl.nasa.gov/dataset/OSCAR_L4_OC_third-deg |

Both datasets have synthetic fallbacks — the app runs fully offline if downloads fail.

---

## Run Commands (in order)

```bash
# 1. Generate synthetic data (always safe to run)
python data/generate_synthetic_data.py

# 2. Attempt real NOAA download (falls back to synthetic on failure)
python data/download_microplastics.py

# 3. Attempt OSCAR current download (falls back to synthetic on failure)
python data/download_currents.py

# 4. Precompute 5-year particle trajectories for all 10 cities
python src/precompute.py

# 5. Launch the dashboard
streamlit run app/streamlit_app.py
```

---

## Methodology

### Lagrangian Particle Advection (Euler Forward Scheme)

Each particle's position is updated at each time step using:

```
lat(t+1) = lat(t) + v(t) * dt / 111320
lon(t+1) = lon(t) + u(t) * dt / (111320 * cos(lat(t)))
```

where `u` and `v` are the eastward and northward surface current velocities (m/s), and `dt = 86400 s` (1 day).

### Current Interpolation

Ocean surface current velocities are interpolated at each particle position using `scipy.interpolate.RegularGridInterpolator` with bilinear (linear) interpolation over the OSCAR 1/3° grid. If the OSCAR file is unavailable, a synthetic analytical field is used:

```
u = 0.1 * cos(lat * π/30)
v = 0.05 * sin(lon * π/60)
```

### Release Configuration

- **10 cities**: Shanghai, Mumbai, Lagos, New York, São Paulo, Jakarta, Dhaka, Manila, Cairo, Los Angeles
- **500 particles per city**, scattered ±0.5° around the city center
- **Simulation duration**: 5 years (1,825 days)

### Land Mask

Particles are halted when they enter rectangular bounding boxes covering major landmasses (North America, South America, Europe, Africa, Asia, Australia, Greenland) or cross polar boundaries (>75°N or <78°S).

---

## Project Structure

```
plasticflow/
├── data/
│   ├── download_microplastics.py   # NOAA download with synthetic fallback
│   ├── download_currents.py        # OSCAR download with synthetic fallback
│   ├── generate_synthetic_data.py  # Standalone synthetic data generator
│   └── processed/                  # Output: microplastics.csv, currents.nc
├── src/
│   ├── simulate.py                 # Core Euler advection engine
│   ├── precompute.py               # Batch simulation for all cities
│   ├── eda.py                      # Exploratory analysis + figures
│   └── correlations.py             # Shipping lane correlation analysis
├── app/
│   └── streamlit_app.py            # 3-page interactive dashboard
├── results/
│   ├── simulation_results/         # trajectories.parquet, final_positions.parquet
│   └── figures/                    # EDA and correlation plots
├── CLAUDE.md
├── requirements.txt
└── README.md
```

---

## Known Limitations

- **Land mask is approximate**: rectangular bounding boxes do not follow precise coastlines; particles near complex coastlines (islands, fjords) may behave unrealistically.
- **No vertical mixing**: the simulation is 2D surface-only; sinking and beaching processes are not modeled.
- **Synthetic current fallback is idealized**: the cosine/sine analytical field captures broad gyre circulation qualitatively but misses seasonal variability and mesoscale eddies.
- **Observation data is synthetic by default**: without a valid NOAA download, all statistical insights reflect synthetic distributions, not real measurements.
- **Euler integration accumulates error**: a 1-day time step with first-order Euler integration introduces drift over 5-year runs; a Runge-Kutta scheme would improve accuracy.

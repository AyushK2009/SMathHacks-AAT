# PlasticFlow — Claude Code Project Guide

## Project Overview
PlasticFlow is a microplastics accumulation analysis and ocean current simulation tool. It combines real NOAA NCEI Marine Microplastics observation data with a Lagrangian particle drift simulation driven by OSCAR ocean surface current data, delivered as an interactive Streamlit dashboard.

## Build Order
Always build files in this exact sequence:
1. requirements.txt
2. data/generate_synthetic_data.py
3. data/download_microplastics.py
4. data/download_currents.py
5. src/simulate.py
6. src/precompute.py
7. src/eda.py
8. src/correlations.py
9. app/streamlit_app.py
10. README.md

## Architecture Rules
- Every data loading function must have a synthetic fallback — never assume downloads succeed
- src/simulate.py is the core engine; all other modules depend on it
- precompute.py must run before the Streamlit app — it generates trajectories.parquet and final_positions.parquet
- app/streamlit_app.py must never run simulations from scratch — always load precomputed results, except for custom lat/lon inputs

## Simulation Specs
- Particles per city: 500
- Cities: Shanghai (31.2,121.5), Mumbai (19.1,72.9), Lagos (6.5,3.4), New York (40.7,-74.0), São Paulo/Santos (-23.9,-46.3), Jakarta (-6.1,106.8), Dhaka/Chittagong (22.3,91.8), Manila (14.6,121.0), Cairo/Alexandria (31.2,29.9), Los Angeles (33.7,-118.2)
- Simulation duration: 5 years (1,825 days)
- Time step: dt = 86400 seconds (1 day)
- Advection scheme: Euler forward step
- Current interpolation: scipy.interpolate.RegularGridInterpolator (bilinear)
- Fallback current field: u = 0.1*cos(lat*π/30), v = 0.05*sin(lon*π/60)
- Land mask: stop particles on land contact

## Performance Rules
- Always vectorize particle operations across all 500 particles using numpy — never use per-particle Python loops
- Cache all heavy computations with @st.cache_data in Streamlit
- Save trajectories as parquet (not CSV) for speed
- Precomputed results live in results/simulation_results/

## Data Sources
- Microplastics: NOAA NCEI Marine Microplastics Database (CSV/GeoJSON)
- Ocean currents: OSCAR monthly climatology (NASA, NetCDF, 1/3° resolution)
- Shipping lanes: synthetic proxy based on major routes (trans-Pacific, trans-Atlantic, Indian Ocean)

## Directory Structure
plasticflow/
├── data/
│   ├── download_microplastics.py
│   ├── download_currents.py
│   ├── generate_synthetic_data.py
│   └── processed/
├── src/
│   ├── simulate.py
│   ├── precompute.py
│   ├── eda.py
│   └── correlations.py
├── app/
│   └── streamlit_app.py
├── results/
│   ├── simulation_results/
│   └── figures/
├── CLAUDE.md
├── requirements.txt
└── README.md

## Error Handling
- If any real data download fails, fall through to synthetic data silently with a console warning
- If trajectories.parquet is missing when the app loads, display a clear error: "Run python src/precompute.py first"
- Never let a missing file crash the app silently

## Run Commands
pip install -r requirements.txt
python data/generate_synthetic_data.py
python data/download_microplastics.py
python data/download_currents.py
python src/precompute.py
streamlit run app/streamlit_app.py

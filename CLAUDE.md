# PlasticFlow

Data Science hackathon project for NC SMathHacks (36-hour hackathon, theme "Under the Sea").

## Project Overview

Analyze global microplastics distribution using NOAA NCEI data, perform statistical analysis, and run a Lagrangian particle drift simulation using OSCAR ocean surface current vectors to explain why microplastics accumulate in ocean gyres. Frontend is a Streamlit app with interactive Plotly/pydeck visualizations.

### Analysis components
- Geographic distribution of microplastics
- Temporal trends
- Hotspot clustering
- Shipping lane correlation
- Lagrangian particle drift simulation (OSCAR current vectors)

## Repo Structure

```
data/          # Raw and processed data files (CSVs, NetCDF, parquet) — gitignored for large files
src/           # All Python modules (data loading, cleaning, analysis, simulation)
app/           # Streamlit app entry point and page files
results/       # Precomputed simulation trajectories and generated figures
requirements.txt
```

## Conventions

- Python 3.10+
- All data processing functions go in `src/`
- Streamlit pages go in `app/`
- Use parquet for processed data, pickle for simulation results
- Type hints on all function signatures
- Docstrings on all public functions

## Key Libraries

`pandas`, `numpy`, `scipy`, `xarray`, `plotly`, `pydeck`, `streamlit`, `scikit-learn`

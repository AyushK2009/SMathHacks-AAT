# PlasticFlow

**Visualizing the invisible threat in our oceans.**

## Inspiration

Microplastics present a massive but largely invisible threat to marine ecosystems. While we frequently see images of macro-plastics like bottles and bags washing ashore, the true scale of the problem lies suspended within the ocean's layers. This project directly solves the problem of disconnected oceanic data—environmental researchers, policy-makers, and ocean cleanup initiatives often struggle to bridge the gap between static historical observation data and the dynamic fluid mechanics of the ocean. 

We were inspired to build **PlasticFlow** to empower these stakeholders with a comprehensive, unified platform. By allowing users to not just see *where* microplastics are currently concentrated but understand the physical oceanographic reasons *why* they accumulate there, PlasticFlow enables data-driven decisions for targeted cleanup efforts, shipping route regulations, and environmental policy drafting.

## What it does

PlasticFlow is an interactive geospatial data dashboard built with Streamlit that takes raw ocean data and transforms it into an intuitive, causal narrative about global microplastic pollution. Rather than present disconnected technical modules, the system is designed to walk users through a logical story: we start with empirical **microplastic observations**, systematically detect **pollution hotspots**, explain those hotspots using **global ocean currents**, and finally prove the mechanism by running a predictive **particle drift simulation** that reproduces the observed accumulation patterns.

### The End-to-End System Pipeline
Our architecture follows a robust data pipeline: 
1. **Raw Data Ingestion**: Pulling NOAA NCEI microplastic observation data and Earth Space Research (ESR) OSCAR NetCDF ocean surface velocity grids.
2. **Preprocessing**: Filtering anomalous readings, standardizing geographic coordinates, and utilizing `xarray` and `dask` for lazy-loading massive ocean current time slices.
3. **Statistical Analysis**: Computing geometric means, temporal trends, and rank correlations.
4. **Geospatial Clustering**: Applying density-based clustering to isolate severe accumulation zones.
5. **Current Integration & Simulation**: Merging historical observations with vector fields to run a Lagrangian Euler advection model.
6. **Visualization**: Serving the precomputed simulation trajectories, clustered polygons, and raw data through an interactive Streamlit frontend rendered via `pydeck` and `plotly`.

### The User Workflow
When users launch PlasticFlow, they interact with a seamless dashboard. They can toggle specific ocean basins, filter historical timeframes, and interact with the 3D globe. They provide parameters such as a starting coordinate and an initial scatter radius for the drift simulation. The interface instantly translates these inputs into visual insights—rendering predictive particle trajectories over a 5-year span to show exactly where their "virtual plastic" will end up.

### 1. Global Observation Map & Hotspot Clustering
We begin by visualizing over 12,000 historical microplastic measurements from the NOAA NCEI database. Because plotting thousands of raw points can be visually overwhelming, we implemented a density-based clustering algorithm.
- **DBSCAN Clustering**: We use Density-Based Spatial Clustering of Applications with Noise (DBSCAN) to algorithmically identify the most severe accumulation zones (hotspots). We use the Haversine formula as our distance metric to correctly account for the Earth's curvature when calculating the distance between observation points:
$$ d = 2r \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos\phi_1\cos\phi_2\sin^2\left(\frac{\Delta\lambda}{2}\right)}\right) $$
Where $\phi$ is latitude, $\lambda$ is longitude, and $r$ is Earth's radius (6371 km). 

### 2. Statistical Analysis & Temporal Trends
Understanding *where* plastic is located isn't enough; we need to understand *why*. Our statistics page runs non-linear correlations between microplastic density and geographic variables.
- **Spearman Rank Correlation**: Because the relationship between plastic density and variables like "distance to coast" or "ocean depth" is monotonic but not linear, we calculate the Spearman rank correlation coefficient:
$$ \rho = 1- {\frac {6 \sum d_i^2}{n(n^2 - 1)}} $$
Where $d_i$ is the difference in paired ranks and $n$ is the number of observations.

### 3. Ocean Surface Currents Data (OSCAR)
To explain the formation of the hotspots identified in step one, we integrate OSCAR datasets providing global ocean surface current velocities derived from satellite altimeter and scatterometer data. On the frontend, we use `pydeck` to render an animated grid of thousands of moving current vectors, giving users a visceral understanding of how water moves across the globe.

### 4. Lagrangian Particle Drift Simulation & Validation
This is the core predictive feature of PlasticFlow. We ask: *If a piece of plastic enters the ocean at point A, where will the ocean currents take it over the next 5 years?*
- **Euler Advection**: We run a Lagrangian drift simulation using Euler integration. For $N$ particles scattered randomly around a starting coordinate, we look up the local OSCAR $u$ (east-west) and $v$ (north-south) velocities.
- **Vectorized Math**: To make this performant in Streamlit, we completely vectorized the simulation using `scipy.ndimage.map_coordinates`. Instead of updating one particle at a time, we bilinearly interpolate the velocity grid for *all* particles simultaneously in a massive NumPy array, providing a ~1000x speedup over brute-force methods. The positions are updated via:
$$ \Delta lat = v \times \frac{seconds\_per\_day}{\text{meters\_per\_degree}} \times \Delta t $$
$$ \Delta lon = u \times \frac{seconds\_per\_day}{\text{meters\_per\_degree} \times \cos(lat)} \times \Delta t $$
- **Quantitative Results / Validation**: The output is an animated trajectory map showing how particles released off the coast of California or Japan inevitably get swept into the Great Pacific Garbage Patch. This provides strong validation for the system—the theoretical simulated drift patterns perfectly align with the empirical hotspot polygons we algorithmically clustered in step one.

## How we built it

The technical novelty of PlasticFlow lies in unifying disparate domains: it takes static, empirical microplastic observations and weds them to dynamic ocean current vector fields and Lagrangian drift simulations in a single, real-time interactive platform.

We utilized **Python (3.10+)** as our core language, leveraging **pandas**, **numpy**, and **scikit-learn** for our data processing and statistical analysis. We pulled in NOAA NCEI microplastic observation data, combining it with OSCAR ocean surface current NetCDF files using `xarray`. For the frontend, we built a **Streamlit** application containing interactive geographic visualizations generated through **Plotly** and **pydeck**. To ensure the Streamlit app was performant, we precomputed the Lagrangian drift simulations and saved processed artifacts in efficient `.parquet` formats.

## Challenges we ran into

One of our primary challenges was processing the massive **ocean currents datasets**. Working with large time-series NetCDF files representing vector fields across the globe required careful memory management and optimization. 

Additionally, building a **digestible UI** was tough. We needed to translate heavy data analysis—like scatter clustering, temporal trendlines, and vector simulations—into an intuitive layout that a non-technical user could understand without feeling overwhelmed. Tuning pydeck to handle thousands of rendered points without lag took several iterations.

Lastly, we had to address critical **Model Assumptions and Limitations**. The current system simulates surface-only ocean currents and operates without factoring in wind forcing (Stokes drift) or complex particle behavior (such as degradation rates, vertical sinking, or beaching dynamics). Balancing scientific accuracy with computational scope during the hackathon was a delicate tightrope to walk.

## Accomplishments that we're proud of

We are incredibly proud of the Lagrangian particle drift simulation, which beautifully visualizes how individual microplastic particles are transported over time by ocean surface currents. Proving the causal narrative—by showing that our virtual particles naturally accumulate in the exact regions we identified as empirical hotspots in the observational data—is our biggest and most satisfying win.

## What we learned

We learned a tremendous amount about handling big geospatial data. We gained practical experience using `xarray` to manipulate multi-dimensional NetCDF arrays efficiently. We also learned how crucial precomputation and vectorized numpy operations are for building highly responsive, performant data dashboards.

## What's next for PlasticFlow

PlasticFlow has immense potential for **Real-World Applications**. For research planning, it can help marine biologists target their sampling expeditions to regions predicted to be high-accumulation zones. For pollution monitoring and policy making, identifying the origin points that feed into major ocean gyres can help governments strategically regulate shipping lanes or target river-mouth cleanup operations.

In the future, we want to integrate predictive machine learning models to forecast where new microplastic hotspots will form based on changing ocean current patterns and increased global shipping. We'd also like to scale our ingestion pipeline to automatically pull and process the latest datasets as they are published by NOAA, and eventually incorporate wind-forcing and 3D subsurface currents to make the drift simulations even more physically accurate.

## Built with
Python 3.10+, Streamlit, Pandas, NumPy, SciPy, Scikit-learn, Xarray, NetCDF4, Plotly, Pydeck, Apache Parquet, PyArrow

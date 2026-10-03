# Emission Impossible — prototype

A flat-folder proof of the pipeline: collect data → transform & join → Streamlit dashboard.
Reference only; the production version moves the collectors into GCS + FastAPI.

## Setup
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

## Get the data (into ./data/)
# EIA CO2 needs no key. BEA + EIA API need free keys in a .env file:
#   EIA_API_KEY=...
#   BEA_API_KEY=...
python collect_local.py

## Run the dashboard
streamlit run app.py

## What's what
- collect_local.py   download each source into ./data/
- transform.py       reshape + join CO2 and GDP on (state, year) + carbon intensity
- app.py             Streamlit dashboard (map, decoupling, state trend, GDP vs CO2)
- data_inspection.ipynb   walk-through of each source and the join
- main.py                 the FastAPI/GCS ingest entry
- user_definition.py    project/bucket/credentials config
- inspect_eia.py     tiny helper (optional, but it documents the sheet-layout gotcha)

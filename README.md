# Emission Impossible — prototype

A flat-folder proof of the pipeline: collect data → transform & join → Streamlit dashboard.
Reference only; the production version moves the collectors into GCS + FastAPI.

## Setup

    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

## Get the data

EIA CO2 needs no API key. BEA and the EIA API need free keys — put them in a `.env` file:

    EIA_API_KEY=your_key_here
    BEA_API_KEY=your_key_here

Then download every source into `./data/` by running:

    python collect_local.py

## Run the dashboard

    streamlit run app.py

## What's what

| File | What it does |
| ---- | ------------ |
| `collect_local.py` | Downloads each data source into `./data/` |
| `transform.py` | Reshapes + joins CO2 and GDP on (state, year); adds carbon intensity |
| `app.py` | Streamlit dashboard — map, decoupling, state trend, GDP vs CO2 |
| `main.py` | FastAPI / GCS ingest entry point |
| `user_definition.py` | Project / bucket / credentials config |
| `data_inspection.ipynb` | Walk-through of each source and the join |
| `inspect_eia.py` | Helper (optional) — documents the Excel sheet-layout gotcha |
| `requirements.txt` | Python dependencies |

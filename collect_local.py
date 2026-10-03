"""
Local prototype collector. Downloads each data source to ./data/ as raw files.
No GCS, no FastAPI -- just run it and look at what lands in ./data/.

    pip install requests python-dotenv
    python collect_local.py

Free API keys go in a .env next to this file:
    EIA_API_KEY=...   get at https://www.eia.gov/opendata/register.php
    BEA_API_KEY=...   get at https://apps.bea.gov/API/signup/
Source 1 (EIA CO2 workbooks) needs NO key -- it's a public file download, so it
runs immediately. The other sources skip with a message until you add the keys.
"""

import os
import datetime

import requests
from dotenv import load_dotenv

load_dotenv()
EIA_API_KEY = os.getenv("EIA_API_KEY")
BEA_API_KEY = os.getenv("BEA_API_KEY")

TODAY = datetime.date.today().strftime("%Y-%m-%d")


def save_local(source, filename, content):
    """Save content under ./data/<source>/<today>/<filename>; return the path.

    Handles both bytes (the .xlsx downloads) and text (the JSON API responses).
    """
    folder = os.path.join("data", source, TODAY)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    mode = "wb" if isinstance(content, (bytes, bytearray)) else "w"
    with open(path, mode) as f:
        f.write(content)
    return path


# ---------------------------------------------------------------------
# Source 1 -- EIA CO2 workbooks (file download, NO key needed)
# ---------------------------------------------------------------------
EIA_CO2_FILES = {
    "co2_total": "https://www.eia.gov/state/seds/sep_sum/html/xls/CO2_total.xlsx",
    "co2_source": "https://www.eia.gov/state/seds/sep_sum/html/xls/CO2_source.xlsx",
    "co2_sector": "https://www.eia.gov/state/seds/sep_sum/html/xls/CO2_sector.xlsx",
}


def collect_eia_co2():
    saved = []
    for url in EIA_CO2_FILES.values():
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        saved.append(save_local("eia_co2", url.split("/")[-1], resp.content))
    return saved


# ---------------------------------------------------------------------
# Source 2 -- BEA real GDP by state (API)
# ---------------------------------------------------------------------
def collect_bea_gdp():
    resp = requests.get(
        "https://apps.bea.gov/api/data/",
        params={
            "UserID": BEA_API_KEY,
            "method": "GetData",
            "datasetname": "Regional",
            "TableName": "SAGDP9",   # real GDP, chained 2017 dollars
            "LineCode": "1",          # all-industry total
            "GeoFips": "STATE",       # every state
            "Year": "ALL",
            "ResultFormat": "JSON",
        },
        timeout=60,
    )
    resp.raise_for_status()
    return [save_local("bea_gdp", "bea_gdp.json", resp.text)]


# ---------------------------------------------------------------------
# Source 3 -- EIA electricity generation (API)
# NOTE: these EIA v2 params are a best-effort starting point. If the response is
# empty or errors, open the facet list in a browser with your key to see valid
# codes, e.g.:
# https://api.eia.gov/v2/electricity/electric-power-operational-data/facet/fueltypeid?api_key=YOUR_KEY
# ---------------------------------------------------------------------
def collect_eia_generation():
    resp = requests.get(
        "https://api.eia.gov/v2/electricity/electric-power-operational-data/data/",
        params={
            "api_key": EIA_API_KEY,
            "frequency": "annual",     # smaller than monthly while prototyping
            "data[0]": "generation",
            "start": "2001",
            "length": 5000,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return [save_local("eia_generation", "eia_generation.json", resp.text)]


# ---------------------------------------------------------------------
# Source 4 -- EIA SEDS energy prices (API, same key as Source 3)
# NOTE: best-effort params; if empty, verify the route/series against EIA's SEDS
# API docs. CLEID = coal price (electric power), ESRCD = residential electricity
# price, ESTCD = all-sector electricity price.
# ---------------------------------------------------------------------
def collect_eia_prices():
    resp = requests.get(
        "https://api.eia.gov/v2/seds/data/",
        params={
            "api_key": EIA_API_KEY,
            "frequency": "annual",
            "data[0]": "value",
            "facets[seriesId][]": ["ESRCD", "ESTCD", "CLEID"],
            "start": "1997",
            "length": 5000,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return [save_local("eia_prices", "eia_prices.json", resp.text)]


def main():
    # (label, function, is it ready to run?)
    jobs = [
        ("EIA CO2 (file, no key)", collect_eia_co2, True),
        ("BEA GDP (API)", collect_bea_gdp, bool(BEA_API_KEY)),
        ("EIA generation (API)", collect_eia_generation, bool(EIA_API_KEY)),
        ("EIA prices (API)", collect_eia_prices, bool(EIA_API_KEY)),
    ]
    for label, fn, ready in jobs:
        if not ready:
            print(f"SKIP  {label} -- set its API key in .env first")
            continue
        try:
            for path in fn():                      # one collector failing...
                print(f"SAVED {label}: {path}")
        except Exception as exc:                    # ...doesn't stop the others
            print(f"FAIL  {label}: {exc}")


if __name__ == "__main__":
    main()

"""
Turn the raw downloaded files into one tidy analysis table and derive the
decoupling fields.

The ONLY file-layout-sensitive piece is load_co2_total(). Everything below it
works on the tidy schema  state | year | co2 | gdp , so if the EIA sheet layout
differs from what the parser assumes, you only fix that one function and the
whole analysis + app keep working. Run inspect_eia.py first to see your layout.
"""

import glob
import json
import os

import pandas as pd

# State full-name -> 2-letter code; used to normalize both sources to one key.
STATE_ABBREV = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
    "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME",
    "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE",
    "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}
_ABBRS = set(STATE_ABBREV.values())


def _to_abbr(label):
    """Map a state name OR 2-letter code to its 2-letter code; None if not a state."""
    s = str(label).strip()
    if s in _ABBRS:
        return s
    if s in STATE_ABBREV:
        return STATE_ABBREV[s]
    return STATE_ABBREV.get(s.title())   # handles 'ALABAMA' / 'alabama'


def _is_year(v):
    try:
        return 1960 <= int(float(v)) <= 2035
    except (ValueError, TypeError):
        return False


def _latest(source, pattern):
    """Newest matching file under data/<source>/<date>/<pattern>."""
    files = sorted(glob.glob(os.path.join("data", source, "*", pattern)))
    if not files:
        raise FileNotFoundError(f"No {pattern} found under data/{source}/")
    return files[-1]


# =====================================================================
# EIA CO2 -- the one layout-sensitive parser (verify against your file)
# =====================================================================
def load_co2_total(path=None, sheet="Total CO2", value_name="co2"):
    """Parse one sheet of CO2_total.xlsx into tidy [state, year, <value_name>].

    It auto-detects the header row (the row with the most 4-digit years) and the
    state column (the column whose values best match U.S. states), so it survives
    the workbook's title/notes rows. If the result looks wrong, run inspect_eia.py
    and adjust `sheet` or this function.

    NOTE: sheet 0 of CO2_total.xlsx is a "Contents" cover page (no data), so the
    default targets the "Total CO2" sheet, where the actual state-by-year totals
    live. The other sheets (Per capita, CO2 per million dollars, ...) are derived
    metrics -- point `sheet` at one of those if you ever want them instead.
    """
    path = path or _latest("eia_co2", "CO2_total.xlsx")
    raw = pd.read_excel(path, sheet_name=sheet, header=None)

    # header row = the one containing the most year-looking cells
    header_i = max(range(len(raw)),
                   key=lambda i: sum(_is_year(v) for v in raw.iloc[i]))
    header = raw.iloc[header_i]
    body = raw.iloc[header_i + 1:]

    # Work by column POSITION (iloc), never by name -- EIA header rows often have
    # blank/duplicate cells, which makes name-based indexing return DataFrames.
    year_pos = [j for j in range(raw.shape[1]) if _is_year(header.iloc[j])]
    years = [int(float(header.iloc[j])) for j in year_pos]

    # state column = the column whose cells match the most U.S. states
    state_pos = max(range(raw.shape[1]),
                    key=lambda j: body.iloc[:, j].map(_to_abbr).notna().sum())

    # build a clean, uniquely-named frame, then melt to long
    tidy = pd.DataFrame({"state": body.iloc[:, state_pos].map(_to_abbr).values})
    for j, yr in zip(year_pos, years):
        tidy[yr] = pd.to_numeric(body.iloc[:, j], errors="coerce").values
    tidy = tidy[tidy["state"].notna()]            # drops US total, regions, notes

    long = tidy.melt(id_vars="state", var_name="year", value_name=value_name)
    long["year"] = long["year"].astype(int)
    return long.dropna(subset=[value_name]).reset_index(drop=True)


# =====================================================================
# BEA real GDP -- stable JSON shape
# =====================================================================
def load_bea_gdp(path=None):
    """Parse the saved BEA JSON into tidy [state, year, gdp].

    Raises a clear message (not a KeyError) when the JSON is a BEA *error*
    response instead of data -- usually a bad/missing BEA_API_KEY or wrong params.
    """
    path = path or _latest("bea_gdp", "bea_gdp.json")
    with open(path) as f:
        payload = json.load(f)

    api = payload.get("BEAAPI", {})
    results = api.get("Results", {})
    data = results.get("Data") if isinstance(results, dict) else None
    if not data:
        err = api.get("Error") or (results.get("Error")
                                   if isinstance(results, dict) else None)
        raise ValueError(
            "BEA JSON has no data -- likely a bad/missing BEA_API_KEY or wrong "
            "params. Fix it and re-run collect_local.py. BEA said: "
            f"{err or payload}")

    df = pd.DataFrame(data)
    df["state"] = df["GeoName"].map(_to_abbr)
    df = df[df["state"].notna()]
    df["year"] = df["TimePeriod"].astype(int)
    df["gdp"] = pd.to_numeric(df["DataValue"].astype(str).str.replace(",", ""),
                              errors="coerce")
    return df[["state", "year", "gdp"]].dropna().reset_index(drop=True)


# =====================================================================
# Join + derived fields
# =====================================================================
def build_dataset():
    """CO2 + GDP joined on (state, year), with carbon intensity added."""
    co2 = load_co2_total()
    gdp = load_bea_gdp()
    df = co2.merge(gdp, on=["state", "year"], how="inner")
    # tonnes CO2 per million $ of real GDP (CO2 is million tonnes, GDP million $).
    df["intensity"] = df["co2"] / df["gdp"] * 1_000_000
    return df.sort_values(["state", "year"]).reset_index(drop=True)


def _classify(pct_gdp, pct_co2):
    """Decoupling category from % change in GDP and CO2 over a window."""
    if pct_gdp <= 0:
        return "Contraction"
    if pct_co2 < 0:
        return "Absolute decoupling"      # GDP up, CO2 down
    if pct_co2 < pct_gdp:
        return "Relative decoupling"       # both up, CO2 slower
    return "No decoupling"                 # CO2 up as fast or faster


def decoupling_table(df, start_year, end_year):
    """One row per state: % change in GDP, CO2, intensity, and the category."""
    a = df[df["year"] == start_year].set_index("state")
    b = df[df["year"] == end_year].set_index("state")
    states = sorted(a.index.intersection(b.index))

    out = pd.DataFrame({"state": states})
    out["pct_gdp"] = [(b.loc[s, "gdp"] / a.loc[s, "gdp"] - 1) * 100 for s in states]
    out["pct_co2"] = [(b.loc[s, "co2"] / a.loc[s, "co2"] - 1) * 100 for s in states]
    out["pct_intensity"] = [(b.loc[s, "intensity"] / a.loc[s, "intensity"] - 1) * 100
                            for s in states]
    out["category"] = [_classify(g, c) for g, c in zip(out["pct_gdp"], out["pct_co2"])]
    return out

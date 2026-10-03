"""
Emission Impossible -- analysis dashboard (reads the tidy table from transform.py).

    pip install -r requirements.txt
    streamlit run app.py

Four views:
  1. Map (levels)      -- any state, any year, colored by CO2 / GDP / intensity.
  2. Decoupling        -- % change between two years: a map + a scatter + a table.
  3. State trend       -- one state's CO2, GDP, and intensity over time.
  4. GDP vs CO2        -- one state, re-based to a chosen start year (decoupling).
"""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import transform

# Fixed colors for the four decoupling categories (identity, not magnitude).
CATEGORY_COLORS = {
    "Absolute decoupling": "#2E7D32",   # green  -- best
    "Relative decoupling": "#9E9D24",   # olive
    "No decoupling": "#C62828",         # red    -- worst
    "Contraction": "#616161",           # gray   -- economy shrank
}

# Line colors for the GDP-vs-CO2 view (kept consistent across the dashboard).
GDP_C, CO2_C, INT_C = "#3987e5", "#d95926", "#199e70"


@st.cache_data(show_spinner="Building the dataset...")
def get_data():
    return transform.build_dataset()


def state_view(df):
    """One state's GDP, CO2, and intensity over a chosen window, all indexed to 100."""
    st.subheader("Does GDP pull away from CO₂?")
    st.caption(
        "All three lines are re-based to 100 at your chosen start year and share one "
        "axis, so you're never comparing dollars to tonnes directly. When GDP climbs "
        "while CO₂ stays flat or falls, the economy is decoupling."
    )

    states = sorted(df["state"].unique())
    yrs = sorted(int(y) for y in df["year"].unique())

    # controls: three dropdowns -- state, start year, end year
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        default = states.index("CA") if "CA" in states else 0
        state = st.selectbox("State", states, index=default, key="sv_state")
    with c2:
        start = st.selectbox("Start year", yrs[:-1], index=0, key="sv_start")
    with c3:
        # end options are only years after the chosen start, so it can't be invalid
        end_opts = [y for y in yrs if y > start]
        end = st.selectbox("End year", end_opts, index=len(end_opts) - 1, key="sv_end")

    # one state, the chosen window, re-based so the start year = 100
    s = df[(df["state"] == state) & (df["year"].between(start, end))].sort_values("year")
    base = s[s["year"] == start].iloc[0]
    s = s.assign(
        gdp_i=s["gdp"] / base["gdp"] * 100,
        co2_i=s["co2"] / base["co2"] * 100,
        int_i=s["intensity"] / base["intensity"] * 100,
    )

    # chart title as a Streamlit heading (keeps it off the Plotly legend -> no overlap)
    st.markdown(f"**{state} — real GDP vs CO₂ emissions  ({start} = 100)**")

    # three indexed lines on one axis
    fig = go.Figure()
    fig.add_hline(y=100, line=dict(color="#888888", dash="dash", width=1))
    fig.add_trace(go.Scatter(x=s["year"], y=s["gdp_i"], name="Real GDP",
                             line=dict(color=GDP_C, width=2.5)))
    fig.add_trace(go.Scatter(x=s["year"], y=s["co2_i"], name="CO₂ emissions",
                             line=dict(color=CO2_C, width=2.5)))
    fig.add_trace(go.Scatter(x=s["year"], y=s["int_i"], name="Carbon intensity",
                             line=dict(color=INT_C, width=2.5, dash="dot")))
    fig.update_layout(
        xaxis_title=None, yaxis_title=f"Index  ({start} = 100)",
        legend=dict(orientation="h", y=1.1, x=0),
        margin=dict(l=0, r=0, t=30, b=0), height=470,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "The gap between the GDP and CO₂ lines is the decoupling. Try CA 1997→2024 "
        "(fans wide open) versus 1997→2007 (barely separates — the clean-up came later)."
    )


st.set_page_config(page_title="Emission Impossible", layout="wide")
st.title("Emission Impossible -- US carbon decoupling")

df = get_data()
years = sorted(int(y) for y in df["year"].unique())  # plain ints -> clean st.slider

tab_levels, tab_change, tab_trend, tab_state = st.tabs(
    ["Map (levels)", "Decoupling (change)", "State trend", "GDP vs CO₂"])

# ---------------------------------------------------------------------
# 1. LEVELS MAP -- magnitude, so a sequential (one-hue) color scale.
# ---------------------------------------------------------------------
with tab_levels:
    METRICS = {
        "Carbon intensity (CO2 per $GDP)": ("intensity", "tonnes / $M"),
        "CO2 emissions": ("co2", "million tonnes"),
        "Real GDP": ("gdp", "$M (2017)"),
    }
    c1, c2 = st.columns([2, 3])
    with c1:
        metric = st.selectbox("Color by", list(METRICS))
    with c2:
        year = st.slider("Year", years[0], years[-1], years[-1])
    col, unit = METRICS[metric]

    year_df = df[df["year"] == year]
    fig = px.choropleth(
        year_df, locations="state", locationmode="USA-states",
        color=col, scope="usa", color_continuous_scale="OrRd",
        labels={col: unit}, hover_name="state",
    )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------
# 2. DECOUPLING -- % change over a window. The map is polarity
#    (improved vs worsened), so a DIVERGING scale centered at 0.
# ---------------------------------------------------------------------
with tab_change:
    c1, c2 = st.columns(2)
    with c1:
        start = st.selectbox("Start year", years, index=0)
    with c2:
        end = st.selectbox("End year", years, index=len(years) - 1)

    if end <= start:
        st.warning("Pick an end year after the start year.")
    else:
        table = transform.decoupling_table(df, start, end)

        # Map: % change in carbon intensity (negative = cleaner = good).
        map_fig = px.choropleth(
            table, locations="state", locationmode="USA-states",
            color="pct_intensity", scope="usa",
            color_continuous_scale="RdBu_r", color_continuous_midpoint=0,
            labels={"pct_intensity": "% change in intensity"},
            hover_name="state",
        )
        map_fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.subheader(f"Change in carbon intensity, {start} → {end}")
        st.caption("Blue = intensity fell (cleaner growth). Red = intensity rose.")
        st.plotly_chart(map_fig, use_container_width=True)

        # Scatter: GDP %change vs CO2 %change; points below y=x grew cleaner.
        st.subheader("GDP vs CO2 change (points below the line decoupled)")
        scat = px.scatter(
            table, x="pct_gdp", y="pct_co2", color="category",
            color_discrete_map=CATEGORY_COLORS, hover_name="state",
            labels={"pct_gdp": "% change GDP", "pct_co2": "% change CO2"},
        )
        lo = min(table["pct_gdp"].min(), table["pct_co2"].min())
        hi = max(table["pct_gdp"].max(), table["pct_co2"].max())
        scat.add_shape(type="line", x0=lo, y0=lo, x1=hi, y1=hi,
                       line=dict(dash="dash", color="gray"))
        scat.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(scat, use_container_width=True)

        st.dataframe(table, use_container_width=True)

# ---------------------------------------------------------------------
# 3. STATE TREND -- one state over time (single series, one axis each).
# ---------------------------------------------------------------------
with tab_trend:
    state = st.selectbox("State", sorted(df["state"].unique()))
    sdf = df[df["state"] == state].sort_values("year")
    for col, title in [("intensity", "Carbon intensity"),
                       ("co2", "CO2 emissions"),
                       ("gdp", "Real GDP")]:
        line = px.line(sdf, x="year", y=col, markers=True, title=title)
        line.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=250)
        st.plotly_chart(line, use_container_width=True)

# ---------------------------------------------------------------------
# 4. GDP vs CO2 -- one state, re-based to a chosen start year (decoupling).
# ---------------------------------------------------------------------
with tab_state:
    state_view(df)

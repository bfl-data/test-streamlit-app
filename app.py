import streamlit as st
import pandas as pd
import numpy as np

import altair as alt

st.set_page_config(page_title="Streamlit: Charts & Maps", page_icon="📈", layout="wide")

@st.cache_data
def make_data(seed: int = 42, days: int = 120):
    rng = np.random.default_rng(seed)
    end = pd.Timestamp.today().normalize()
    dates = pd.date_range(end - pd.Timedelta(days=days-1), end, freq="D")

    # City centers (approx) — India focus
    cities = {
        "Pune": (18.5204, 73.8567),
        "Mumbai": (19.0760, 72.8777),
        "Delhi": (28.6139, 77.2090),
        "Bengaluru": (12.9716, 77.5946),
    }

    rows = []
    for city, (lat, lon) in cities.items():
        base_orders = rng.integers(80, 200)       # baseline orders
        noise = rng.normal(0, 20, size=len(dates)) # some daily variation
        trend = np.linspace(-10, 10, len(dates))   # small trend
        orders = np.clip(base_orders + noise + trend, 10, None).round().astype(int)

        # Price per order (varies by city)
        price = {
            "Pune": 350.0, "Mumbai": 420.0, "Delhi": 390.0, "Bengaluru": 410.0
        }[city]
        revenue = orders * (price + rng.normal(0, 15, size=len(dates)))

        for d, o, r in zip(dates, orders, revenue):
            rows.append((d, city, o, float(r), lat, lon))

    df = pd.DataFrame(rows, columns=["date", "city", "orders", "revenue", "lat", "lon"])
    df["date"] = pd.to_datetime(df["date"])
    df["weekday"] = df["date"].dt.day_name()

    # Also make a point cloud around city centers for map layers (scatter/hex)
    pts = []
    for city, (lat, lon) in cities.items():
        # 400 random points around the city center
        for _ in range(400):
            # ~1-3 km jitter
            jitter_lat = lat + (rng.normal(0, 0.01))
            jitter_lon = lon + (rng.normal(0, 0.01))
            vol = float(max(0, rng.normal(100, 40)))  # some volume
            pts.append((city, jitter_lat, jitter_lon, vol))
    geo = pd.DataFrame(pts, columns=["city", "lat", "lon", "volume"])

    return df, geo

df, geo = make_data()

st.title("📈 Charts & 🗺️ Maps with Streamlit")
st.caption("A guided tour of quick charts, Altair/Plotly/Matplotlib, and mapping with st.map & pydeck.")

# Sidebar controls to play with the data
st.sidebar.header("Controls")
city_filter = st.sidebar.multiselect("Cities", sorted(df["city"].unique()), default=sorted(df["city"].unique()))
metric = st.sidebar.selectbox("Metric", ["orders", "revenue"], index=1)
days_back = st.sidebar.slider("Days to show", min_value=14, max_value=120, value=60, step=7)
smooth = st.sidebar.checkbox("Show 7D rolling mean (Altair & Plotly demos)")

df_view = df[df["city"].isin(city_filter)].copy()
cutoff = df_view["date"].max() - pd.Timedelta(days=days_back-1)
df_view = df_view[df_view["date"] >= cutoff]

# Optional smoothed column
if smooth:
    df_view["smoothed"] = (
        df_view
        .sort_values(["city", "date"])
        .groupby("city")[metric]
        .transform(lambda s: s.rolling(7, min_periods=1).mean())
    )

st.divider()

# ------------------------------------------------------------
# A) Quick built-in charts
#    These are the fastest way to visualize a tidy DataFrame.
# ------------------------------------------------------------
st.header("A) Quick built-in charts")

st.write("**line_chart / area_chart / bar_chart / scatter_chart** accept DataFrames directly.")

# Prepare a pivoted form: index=date, columns=city, values=metric
pivot = (
    df_view.pivot_table(index="date", columns="city", values=metric, aggfunc="sum")
    .sort_index()
)

c1, c2, c3 = st.columns(3)
with c1:
    st.subheader("st.line_chart")
    st.line_chart(pivot, use_container_width=True)

with c2:
    st.subheader("st.area_chart")
    st.area_chart(pivot, use_container_width=True)

with c3:
    st.subheader("st.bar_chart")
    st.bar_chart(pivot.tail(30), use_container_width=True)  # last 30 days for readability

st.caption("Tip: Put cities on columns and dates on the index for quick multi-series charts.")

st.divider()

# ------------------------------------------------------------
# B) Altair charts (declarative grammar of graphics)
#    Great for analytics and custom encodings.
# ------------------------------------------------------------
st.header("B) Altair (customizable)")

show_points = st.checkbox("Show data points (Altair)", value=False)

alt_df = df_view if not smooth else df_view.assign(value=df_view["smoothed"])
if not smooth:
    alt_df = df_view.assign(value=df_view[metric])

alt_chart = (
    alt.Chart(alt_df)
    .mark_line(point=show_points)
    .encode(
        x=alt.X("date:T", title="Date"),
        y=alt.Y("value:Q", title=metric.capitalize()),
        color=alt.Color("city:N", title="City"),
        tooltip=["date:T", "city:N", alt.Tooltip("value:Q", title=metric)],
    )
    .properties(height=320)
    .interactive()  # zoom & pan
)

st.altair_chart(alt_chart, use_container_width=True)
st.caption("Use `interactive()` for pan/zoom, tooltips for details-on-demand.")

st.divider()
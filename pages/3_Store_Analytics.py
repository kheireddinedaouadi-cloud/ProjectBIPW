import streamlit as st
import plotly.graph_objects as go
from utils.dashboard import *
import database.queries as Q

st.set_page_config(page_title="Store & Regional Analytics | ABC Retail", page_icon="📍", layout="wide")
apply_theme(); sidebar_brand()
page_header("Store & Regional Analytics", "Compare retail locations and evaluate regional contribution", "📍")
all_regions = distinct("Region")
regions = st.multiselect("Region", all_regions, default=all_regions)
P = {"regions": regions}; L = ("regions",)

regional = run(Q.STORE_REGIONAL, P, L)
store = run(Q.STORE_BY_STORE, P, L)

left, right = st.columns(2)
with left:
    panel_title("Revenue by Region", "🗺️")
    fig = go.Figure(go.Bar(x=col(regional, "Region"), y=col(regional, "Revenue_DZD"), marker_color="#197cf3", textposition="outside",
                           text=[format_dzd(v, True) for v in col(regional, "Revenue_DZD")]))
    st.plotly_chart(chart_layout(fig, 340), use_container_width=True)
with right:
    panel_title("Store Revenue Comparison", "🏬")
    fig = go.Figure()
    for r in dict.fromkeys(col(store, "Region")):
        rows = [s for s in store if s["Region"] == r]
        fig.add_trace(go.Bar(x=col(rows, "Revenue_DZD"), y=col(rows, "Store_Name"), orientation="h", name=r))
    st.plotly_chart(chart_layout(fig, 340), use_container_width=True)

panel_title("Store Performance", "📊")
perf = run(Q.STORE_TARGETS, P, L)
st.dataframe(perf, hide_index=True, use_container_width=True)
export_buttons(store[::-1], "abc_retail_store_performance")
st.caption("Target achievement comes from the vw_target_performance view (targets vs actual sales, computed in SQL). Regional/store sales come from vw_clean_sales.")

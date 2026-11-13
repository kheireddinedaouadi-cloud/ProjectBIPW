import streamlit as st
import plotly.graph_objects as go
from utils.dashboard import *
import database.queries as Q

st.set_page_config(page_title="Inventory Monitoring | ABC Retail", page_icon="⚠️", layout="wide")
apply_theme(); sidebar_brand()
page_header("Inventory Monitoring", "Identify stock risks and prioritize replenishment", "⚠️")
t = one(Q.INV_TOTALS)
a, b, c = st.columns(3); a.metric("Inventory records", f"{t['total']:,}"); b.metric("Below reorder level", f"{t['below']:,}"); c.metric("Items to monitor", f"{t['monitor']:,}")

left, right = st.columns(2)
with left:
    panel_title("Stock by Category", "📦")
    stock = run(Q.INV_STOCK_BY_CATEGORY)
    fig = go.Figure(go.Bar(x=col(stock, "Category"), y=col(stock, "stock"), marker_color="#16a66a", text=col(stock, "stock"), textposition="outside"))
    st.plotly_chart(chart_layout(fig, 330), use_container_width=True)
with right:
    panel_title("Inventory Status", "🚦")
    counts = run(Q.INV_STATUS_COUNTS)
    fig = go.Figure(go.Pie(labels=col(counts, "Status"), values=col(counts, "items"), hole=.5, marker=dict(colors=PALETTE)))
    st.plotly_chart(chart_layout(fig, 330), use_container_width=True)

panel_title("Replenishment Alerts", "🔔")
selected = st.selectbox("Region", ["All"] + distinct("Region", "vw_inventory_status"))
view = run(Q.INV_ALERTS, {"region": selected})
st.dataframe(view, hide_index=True, use_container_width=True)
export_buttons(view, "abc_retail_inventory_alerts")
st.caption("Inventory status is assessed in SQL against each product-store reorder level in the latest inventory snapshot (view vw_inventory_status).")

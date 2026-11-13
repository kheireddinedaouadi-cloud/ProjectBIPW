import streamlit as st
import plotly.graph_objects as go
from utils.dashboard import *
import database.queries as Q

st.set_page_config(page_title="Product Analytics | ABC Retail", page_icon="📦", layout="wide")
apply_theme(); sidebar_brand()
page_header("Product Analytics", "Understand product, category and portfolio performance", "📦")
all_cats, all_brands = distinct("Category"), distinct("Brand")
a, b = st.columns([1, 1])
with a: categories = st.multiselect("Product category", all_cats, default=all_cats)
with b: brands = st.multiselect("Brand", all_brands, default=all_brands)
W = Q.PRODUCT_FILTER; P = {"cats": categories, "brands": brands}; L = ("cats", "brands")

k = one(Q.PRODUCT_KPIS, P, L, where=W)
c1, c2, c3 = st.columns(3); c1.metric("Product revenue", format_dzd(k["rev"])); c2.metric("Gross profit", format_dzd(k["profit"])); c3.metric("Units sold", f"{k['qty']:,.0f}")

left, right = st.columns(2)
with left:
    panel_title("Revenue by Category", "🧩")
    cat = run(Q.PRODUCT_BY_CATEGORY, P, L, where=W)
    fig = go.Figure(go.Pie(labels=col(cat, "Category"), values=col(cat, "revenue"), hole=.5, marker=dict(colors=PALETTE)))
    st.plotly_chart(chart_layout(fig, 350), use_container_width=True)
with right:
    panel_title("Top 10 Products by Revenue", "🏆")
    top = run(Q.PRODUCT_TOP, P, L, where=W)[::-1]
    fig = go.Figure()
    for c in dict.fromkeys(col(top, "Category")):       # one trace per category = colour legend
        rows = [r for r in top if r["Category"] == c]
        fig.add_trace(go.Bar(x=col(rows, "revenue"), y=col(rows, "Product_Name"), orientation="h", name=c))
    st.plotly_chart(chart_layout(fig, 350), use_container_width=True)

panel_title("Product Performance Detail", "📋")
full = run(Q.PRODUCT_DETAIL, P, L, where=W)
st.dataframe(full, hide_index=True, use_container_width=True)
export_buttons(full, "abc_retail_product_performance")

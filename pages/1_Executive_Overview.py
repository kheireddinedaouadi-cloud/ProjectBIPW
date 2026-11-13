import streamlit as st
import plotly.graph_objects as go
from utils.dashboard import *
import database.queries as Q

st.set_page_config(page_title="Executive Overview | ABC Retail", page_icon="📈", layout="wide")
apply_theme(); sidebar_brand()
page_header("ABC Retail – Executive Overview", "Real-time business insights for smarter decisions", "📈")
flt = executive_filters()
W, P = scope_where(**flt)          # every number below is a SQL aggregate over this scope

k = one(Q.EXEC_KPIS, P, where=W)
if not k.get("transactions"):
    st.warning("No sales records match the selected filters."); st.stop()

notes = month_comparison(flt)
colors = ["kpi-blue", "kpi-green", "kpi-purple", "kpi-orange", "kpi-teal"]
items = [("Total Revenue", format_dzd(k["revenue"]), "💳", colors[0], "revenue"), ("Gross Profit", format_dzd(k["profit"]), "📈", colors[1], "profit"),
         ("Gross Margin", f"{k['margin']:.1f}%", "%", colors[2], "margin"), ("Transactions", f"{k['transactions']:,}", "🛒", colors[3], "transactions"),
         ("Quantity Sold", f"{k['quantity']:,.0f}", "📦", colors[4], "quantity")]
for c, (label, value, ico, css, key) in zip(st.columns(5), items):
    with c: st.markdown(f'<div class="kpi {css}"><div class="kpi-label">{ico} &nbsp;{label}</div><div class="kpi-value">{value}</div><div class="kpi-note">{notes.get(key, "Selected reporting period")}</div></div>', unsafe_allow_html=True)
st.write("")

SHOW = {"displayModeBar": False}
left, mid, right = st.columns([1.55, 1.05, 1.2], gap="small")
with left:
    panel_title("Monthly Revenue Trend", "📈")
    monthly = run(Q.EXEC_MONTHLY, P, where=W)
    multi_year = len(set(col(monthly, "Year"))) > 1
    x = [f"{r['Mon']} {r['Year']}" if multi_year else r["Mon"] for r in monthly]
    fig = go.Figure(go.Scatter(x=x, y=col(monthly, "revenue"), mode="lines+markers", name="Revenue", line=dict(color="#1477f8", width=3),
                               marker=dict(size=7), fill="tozeroy", fillcolor="rgba(20,119,248,.10)"))
    fig.update_xaxes(tickangle=0); fig.update_yaxes(tickformat=".2s")
    st.plotly_chart(chart_layout(fig, 285), use_container_width=True, config=SHOW)
with mid:
    panel_title("Revenue by Product Category", "🛍️")
    cat = run(Q.EXEC_CATEGORY, P, where=W)
    rows = cat[::-1]    # largest at the top of the horizontal bar
    fig = go.Figure(go.Bar(x=col(rows, "revenue"), y=col(rows, "Category"), orientation="h", marker_color="#7c4dff", cliponaxis=False,
                           text=[f"{r['revenue']/1e6:.1f}M · {r['share']:.0f}%" for r in rows], textposition="outside", textfont=dict(size=12)))
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(showticklabels=False, range=[0, max(col(rows, "revenue")) * 1.6])
    st.plotly_chart(chart_layout(fig, 285), use_container_width=True, config=SHOW)
with right:
    panel_title("Sales by Region", "📍")
    reg = run(Q.EXEC_REGION, P, where=W)
    fig = go.Figure(go.Pie(labels=col(reg, "Region"), values=col(reg, "revenue"), hole=.56, sort=False, textposition="inside", textinfo="percent",
                           textfont=dict(size=13, color="white"), marker=dict(colors=PALETTE, line=dict(color="#eef4ff", width=3))))
    fig.add_annotation(text=f"<b>{k['revenue']/1e6:.1f}M</b><br>DA", showarrow=False, font=dict(size=15, color="#10284b"))
    st.plotly_chart(chart_layout(fig, 285), use_container_width=True, config=SHOW)

left, mid, right = st.columns([1.7, 1.25, 1.25], gap="small")
with left:
    panel_title("Top 10 Products", "🏆")
    top = run(Q.EXEC_TOP_PRODUCTS, P, where=W)[::-1]
    fig = go.Figure(go.Bar(x=col(top, "revenue"), y=col(top, "Product_Name"), orientation="h", marker_color="#2482f5", cliponaxis=False,
                           text=[f"{v/1e6:.1f}M" for v in col(top, "revenue")], textposition="inside"))
    st.plotly_chart(chart_layout(fig, 300), use_container_width=True, config=SHOW)
with mid:
    panel_title("Store Performance", "🏬")
    stores = run(Q.EXEC_STORES, P, where=W)
    fig = go.Figure(go.Bar(x=col(stores, "Store_Name"), y=col(stores, "revenue"), marker_color="#18a957", cliponaxis=False,
                           text=[f"{v/1e6:.1f}M" for v in col(stores, "revenue")], textposition="outside"))
    fig.update_layout(xaxis_tickangle=-25)
    st.plotly_chart(chart_layout(fig, 300), use_container_width=True, config=SHOW)
with right:
    panel_title("Inventory Alerts", "⚠️")
    alerts = run(Q.EXEC_INVENTORY_ALERTS)
    if not alerts: st.success("No inventory alerts for the latest snapshot.")
    else: st.dataframe(alerts, hide_index=True, use_container_width=True, height=260)
with left:
    panel_title("Key Insights", "💡")
    st.markdown(f'<div class="insight">🟢 Revenue for the selected scope is <strong>{format_dzd(k["revenue"])}</strong>.</div><div class="insight">🟢 <strong>{cat[0]["Category"]}</strong> is the leading category in the selected scope.</div><div class="insight">🔵 <strong>{stores[0]["Store_Name"]}</strong> is the highest-revenue store in the selected scope.</div>', unsafe_allow_html=True)
with mid:
    panel_title("Business Recommendations", "🚀")
    recs = ["Prioritize replenishment for products below reorder level.", "Review category and regional mix to focus commercial campaigns.", "Compare store performance with targets before reallocating resources."]
    for i, r in enumerate(recs, 1): st.markdown(f'<div class="insight"><strong>{i}.</strong> {r}</div>', unsafe_allow_html=True)
with right:
    panel_title("Export Data", "📥")
    export_buttons(run(Q.EXEC_EXPORT, P, where=W), "abc_retail_executive_overview")
st.caption("All monetary values are expressed in Algerian dinars (DZD / DA). Inventory alerts use the latest inventory snapshot in the database.")

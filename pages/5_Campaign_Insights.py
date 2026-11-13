import streamlit as st
import plotly.graph_objects as go
from utils.dashboard import *
import database.queries as Q

st.set_page_config(page_title="Campaign Insights | ABC Retail", page_icon="📣", layout="wide")
apply_theme(); sidebar_brand()
page_header("Campaign & Business Insights", "Review campaign activity and compare business indicators", "📣")
campaigns = run(Q.CAMPAIGNS)
t = one(Q.CAMPAIGN_TOTALS)
a, b = st.columns(2)
with a:
    panel_title("Campaign Portfolio", "📣")
    st.metric("Campaigns", f"{t['n']:,}")
    st.metric("Total Campaign Budget", format_dzd(t["budget"]))
with b:
    panel_title("Campaign Budget by Campaign", "💰")
    fig = go.Figure(go.Bar(x=col(campaigns, "Campaign_Name"), y=col(campaigns, "Campaign_Budget_DZD"), marker_color=PALETTE * 2))
    fig.update_layout(showlegend=False, xaxis_tickangle=-25)
    st.plotly_chart(chart_layout(fig, 270), use_container_width=True)
panel_title("Campaign Register", "📋")
st.dataframe(campaigns, hide_index=True, use_container_width=True)
panel_title("Before-and-After Indicators", "↔️")
ba = run(Q.CAMPAIGN_BEFORE_AFTER)
st.dataframe(ba, hide_index=True, use_container_width=True)
st.warning("A before-and-after comparison alone does not establish that a campaign caused the observed change. Consider seasonality, control groups and other influencing factors.")
export_buttons(campaigns, "abc_retail_campaigns")

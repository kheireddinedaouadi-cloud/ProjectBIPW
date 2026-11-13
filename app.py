import streamlit as st
from utils.dashboard import apply_theme, sidebar_brand, page_header, one
import database.queries as Q

st.set_page_config(page_title="ABC Retail | Business Intelligence", page_icon="🛒", layout="wide", initial_sidebar_state="collapsed")
apply_theme()
sidebar_brand()
page_header("ABC Retail Business Intelligence", "An integrated analytical environment for smarter retail decisions", "📊")
st.caption("Data source: SQLite")
st.markdown("### Welcome to your retail performance workspace")
st.write("Use the navigation bar at the top to explore executive performance, product analytics, store and regional results, inventory health, and campaign insights.")
t = one(Q.HOME_TOTALS)
a, b, c = st.columns(3)
a.metric("Sales records", f"{t['records']:,}")
b.metric("Retail stores", f"{t['stores']:,}")
c.metric("Products", f"{t['products']:,}")
st.info("Open **Executive Overview** in the top bar to access the consolidated management dashboard.")

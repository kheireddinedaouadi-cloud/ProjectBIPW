import csv
import io
import re

import streamlit as st

import database.queries as Q
from database.queries import scope_where  # re-exported for the pages
from database.connection import connect, database_ready

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
NAVY = "#092653"
BLUE = "#1477f8"

# ---------------------------------------------------------------- SQLite access
def ensure_db():
    """Build the SQLite file from the Excel workbook on first run; stop the page if that is impossible."""
    if database_ready():
        return
    try:
        from database.etl_load import build_database
        with st.spinner("Building the SQLite database from the Excel workbook (first run only)..."):
            build_database(quiet=True)
        st.cache_data.clear()
    except Exception as exc:
        st.error(f"Cannot open the SQLite database. Run `python database/etl_load.py` first. ({exc})")
        st.stop()

@st.cache_data(ttl=300, show_spinner=False)
def run(sql, params=None, lists=(), where=None, base_where=None):
    """Run a SELECT from database/queries.py and return a list of dicts.

    where / base_where fill the {where} / {base_where} placeholders of the query.
    `lists` names parameters used as `IN :name` (expanded to one placeholder per value).
    """
    params = dict(params or {})
    if where is not None or base_where is not None:
        sql = sql.format(where=where, base_where=base_where)
    for name in lists:
        values = list(params.pop(name))
        marks = ", ".join(f":{name}_{i}" for i in range(len(values))) or "NULL"   # empty list -> matches nothing
        sql = re.sub(rf":{name}\b", f"({marks})", sql)
        params.update({f"{name}_{i}": v for i, v in enumerate(values)})
    conn = connect()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()

def one(sql, params=None, lists=(), where=None, base_where=None):
    rows = run(sql, params, lists, where, base_where)
    return rows[0] if rows else {}

def col(rows, name):
    return [r[name] for r in rows]

def distinct(column, table="vw_clean_sales"):
    return [r[column] for r in run(Q.distinct_query(column, table))]

def apply_theme():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    :root { --navy:#092653; --blue:#1477f8; --ink:#10284b; --muted:#6b7b91; }
    html, body, [class*="css"] { font-family: Inter, sans-serif; }
    .stApp { background: #eef4ff; }
    [data-testid="stHeader"] { background: transparent; height: 0; }
    [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], #MainMenu, footer { display: none !important; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg,#071c3b 0%,#0c2b55 100%); }
    [data-testid="stSidebar"] * { color:#f4f8ff; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#dbe8ff; }
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] { padding-top: .5rem; }
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] a { border-radius:10px; margin:3px 0; }
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover { background:#173f77; }
    .block-container { padding-top:2.2rem; padding-bottom:2rem; max-width: 1600px; }
    h1,h2,h3 { color:var(--ink); letter-spacing:-.035em; }
    .hero { display:flex; align-items:center; gap:15px; margin:0 0 18px 0; }
    .hero-icon { width:52px;height:52px;border-radius:14px;background:#dceaff;color:#1269e8;display:flex;align-items:center;justify-content:center;font-size:29px; }
    .hero-title { font-size:29px;font-weight:800;color:#0a2145;line-height:1.15; }
    .hero-sub { color:#5c6e86;font-size:14px;margin-top:4px; }
    .section-head { background:linear-gradient(90deg,#092653,#123d77); color:white; padding:10px 14px; border-radius:10px 10px 0 0; font-weight:700; font-size:15px; margin-bottom:0; }
    .panel { background:white;border:1px solid #dce6f5;border-radius:11px;box-shadow:0 3px 12px rgba(19,53,95,.07);padding:13px 15px;margin-bottom:13px; }
    .kpi { border-radius:12px; color:white; padding:17px 18px 15px; min-height:118px; box-shadow:0 4px 12px rgba(20,50,90,.13); }
    .kpi-label { font-size:14px;font-weight:600;opacity:.96; }
    .kpi-value { font-size:25px;font-weight:800;letter-spacing:-.03em;margin-top:7px;white-space:nowrap; }
    .kpi-note { font-size:11px;opacity:.92;margin-top:5px; }
    .delta { background:#fff;padding:1px 8px;border-radius:10px;font-weight:800;font-size:11px; }
    .delta-up { color:#0f9d58; } .delta-down { color:#e11d2e; } .delta-flat { color:#64748b; }
    .kpi-blue {background:linear-gradient(135deg,#0755c9,#1685ff);}
    .kpi-green {background:linear-gradient(135deg,#009b68,#12bb87);}
    .kpi-purple {background:linear-gradient(135deg,#6736c8,#9460f3);}
    .kpi-orange {background:linear-gradient(135deg,#f07800,#ffa21a);}
    .kpi-teal {background:linear-gradient(135deg,#00a7b5,#12cbd0);}
    .insight {background:#fff;border:1px solid #dce6f5;border-radius:10px;padding:11px 13px;margin-bottom:8px;color:#1b3558;font-size:13px;}
    .insight strong {color:#0c6cdb;}
    .alert-low {color:#b42318;background:#fee4e2;padding:4px 9px;border-radius:20px;font-weight:700;font-size:11px;}
    .alert-watch {color:#8a5b00;background:#fff0bf;padding:4px 9px;border-radius:20px;font-weight:700;font-size:11px;}
    div[data-testid="stMetric"] {background:white;border:1px solid #dce6f5;padding:12px 14px;border-radius:11px;box-shadow:0 2px 8px rgba(19,53,95,.05);}
    div[data-testid="stMetricLabel"] {color:#5c6e86;}
    div[data-testid="stDataFrame"] {border:1px solid #dce6f5;border-radius:9px;overflow:hidden;}
    .stDownloadButton button {border-radius:8px;}
    </style>
    """, unsafe_allow_html=True)

def page_header(title, subtitle, icon="📊"):
    st.markdown(f'<div class="hero"><div class="hero-icon">{icon}</div><div><div class="hero-title">{title}</div><div class="hero-sub">{subtitle}</div></div></div>', unsafe_allow_html=True)

def panel_title(title, icon=""):
    st.markdown(f'<div class="section-head">{icon} {title}</div>', unsafe_allow_html=True)

PALETTE = ["#1477f8","#18a957","#7c4dff","#f59e0b","#14b8c6","#ef4444","#64748b"]

def chart_layout(fig, height=300):
    fig.update_layout(height=height, margin=dict(l=10,r=10,t=26,b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter",color="#10284b",size=13), colorway=PALETTE, legend=dict(orientation="h",y=-0.08,x=0.5,xanchor="center",font=dict(size=12)),
        hoverlabel=dict(bgcolor="white",font=dict(size=13)))
    fig.update_xaxes(showgrid=False, linecolor="rgba(16,40,75,.25)", tickfont=dict(size=12), title_text=None)
    fig.update_yaxes(gridcolor="rgba(16,40,75,.10)", zeroline=False, tickfont=dict(size=12), title_text=None)
    return fig

def format_dzd(value, compact=False):
    value = float(value or 0)
    if compact and abs(value) >= 1_000_000:
        return f"{value/1_000_000:.2f}M DA"
    return f"{value:,.0f} DA"

def _current_page_file():
    """File name of the page script that called sidebar_brand() (e.g. '1_Executive_Overview.py')."""
    import inspect, os
    for fr in inspect.stack()[1:8]:
        name = os.path.basename(fr.filename)
        if name == "app.py" or (name[:1].isdigit() and name.endswith(".py")):
            return name
    return None

NAV = [("app.py", "🏠 Home"), ("pages/1_Executive_Overview.py", "📈 Executive Overview"), ("pages/2_Product_Analytics.py", "📦 Product Analytics"),
       ("pages/3_Store_Analytics.py", "🏬 Store Analytics"), ("pages/4_Inventory_Monitoring.py", "🗃️ Inventory Monitoring"),
       ("pages/5_Campaign_Insights.py", "📣 Campaign Insights")]

def sidebar_brand():
    """Top navigation bar. The button of the page you are on is a *primary* (filled navy) button, the others are white,
    so the user always sees where he is. Also hides the sidebar and makes sure the SQLite database exists."""
    import os
    current = _current_page_file()
    st.markdown("""<style>
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] { display:none !important; }
    /* other pages: white buttons */
    button[kind="secondary"], button[data-testid="stBaseButton-secondary"] { background:#ffffff; border:1px solid #dce6f5; border-radius:10px; color:#10284b; }
    button[kind="secondary"]:hover, button[data-testid="stBaseButton-secondary"]:hover { background:#dceaff; border-color:#1477f8; color:#10284b; }
    /* current page: filled navy, blue ring, white bold text */
    button[kind="primary"], button[data-testid="stBaseButton-primary"] { background:#092653 !important; border:2px solid #1477f8 !important; border-radius:10px;
        box-shadow:0 0 0 4px rgba(20,119,248,.30), 0 6px 14px rgba(9,38,83,.30); color:#ffffff !important; }
    button[kind="primary"] p, button[data-testid="stBaseButton-primary"] p { color:#ffffff !important; font-weight:800; }
    button p { font-size:13px; font-weight:600; }
    </style>""", unsafe_allow_html=True)
    for c, (path, label) in zip(st.columns(len(NAV)), NAV):
        active = os.path.basename(path) == current
        if c.button(label, key=f"nav_{path}", type="primary" if active else "secondary", use_container_width=True) and not active:
            st.switch_page(path)
    ensure_db()

def export_buttons(rows, prefix="abc_retail"):
    if not rows:
        return
    headers = list(rows[0].keys())
    c1, c2 = st.columns(2)
    with c1:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers)
        writer.writeheader(); writer.writerows(rows)
        st.download_button("⬇ Download CSV", buf.getvalue().encode("utf-8-sig"), f"{prefix}.csv", "text/csv", use_container_width=True)
    with c2:
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.title = "Data"
        ws.append(headers)
        for r in rows: ws.append([r[h] for h in headers])
        out = io.BytesIO(); wb.save(out)
        st.download_button("⬇ Download Excel", out.getvalue(), f"{prefix}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

def executive_filters():
    """Renders the filters and returns the selected values (Quarter -> Month -> Region -> Store)."""
    st.markdown("<div style='font-weight:700;color:#19385e;margin:0 0 6px'>Dashboard filters</div>", unsafe_allow_html=True)
    a, b, c, d = st.columns([1, 1, 1.2, 1.2])
    quarters = [f"{r['Year']}-{r['Quarter']}" for r in run(Q.QUARTERS)]
    regions, stores = distinct("Region"), distinct("Store_Name")
    with a:
        quarter = st.selectbox("Quarter", ["All"] + quarters, format_func=lambda x: x if x == "All" else f"{x.split('-')[1]} {x.split('-')[0]}")
    if quarter == "All":                                   # months offered follow the chosen quarter
        months = [r["Month"] for r in run(Q.ALL_MONTHS)]
    else:
        y, q = quarter.split("-")
        months = [r["Month"] for r in run(Q.QUARTER_MONTHS, {"year": int(y), "quarter": q})]
    with b: month = st.selectbox("Month", ["All"] + months, format_func=lambda x: x if x == "All" else MONTHS[int(x) - 1])
    with c: region = st.selectbox("Region", ["All"] + regions)
    with d: store = st.selectbox("Store", ["All"] + stores)
    return dict(quarter=quarter, month=month, region=region, store=store)

def month_comparison(filters):
    """Latest month in the selected scope vs the previous calendar month, computed in SQL with LAG.
    The previous month is looked up with the Region/Store filters only, so it is found across years."""
    full_w, p = scope_where(**filters)
    base_w, _ = scope_where(**filters, dates=False)
    r = one(Q.MONTH_COMPARISON, p, where=full_w, base_where=base_w)
    if not r:
        return {}
    y, m = divmod(int(r["ym"]), 100); py, pm = divmod(int(r["p_ym"]), 100)
    prefix = f"{MONTHS[m-1][:3]} {y}: " if r["n_months"] > 1 else ""   # several months shown -> delta is for the latest one
    notes = {}
    for k in ("revenue", "profit", "margin", "transactions", "quantity"):
        d = r[k]
        if d is None: continue
        txt = f"{d:+.1f} pp" if k == "margin" else f"{d:+.1f}%"
        arrow, cls = ("▲", "delta-up") if d > 0 else (("▼", "delta-down") if d < 0 else ("■", "delta-flat"))
        notes[k] = f'{prefix}<span class="delta {cls}">{arrow} {txt}</span> vs {MONTHS[pm-1][:3]} {py}'
    return notes

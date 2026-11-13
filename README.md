# ABC Retail Business Intelligence Dashboard

A Streamlit multipage BI application using the synthetic ABC Retail dataset.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
```

Then install the dependencies and start the app:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## SQLite data warehouse

The app reads a star schema stored in a single SQLite file, `data/abc_retail.db`
(`dim_product`, `dim_store`, `dim_customer`, `dim_time`, `fact_sales` plus targets, inventory and campaign tables).
There is no server, user or password to set up: SQLite is part of Python's standard library.
All calculations run in SQL; the Python code contains no pandas.

| File | Content |
|------|---------|
| `database/queries.py` | **Every SQL query used by the dashboard**, one named constant per query (`EXEC_KPIS`, `PRODUCT_TOP`, `INV_ALERTS`...) |
| `database/schema.py` | Table definitions and the four views (`vw_clean_sales`, `vw_target_performance`, `vw_inventory_status`, `vw_monthly_kpis`) |
| `database/etl_load.py` | Reads the Excel workbook (openpyxl) and fills the SQLite file |
| `database/connection.py` | Opens the SQLite file (path can be changed with the `ABC_DB_PATH` environment variable) |

The database file is built automatically on first run if it is missing. To rebuild it by hand
(for example after the workbook changes):

```bash
python database/etl_load.py
```

To change or add a query, edit `database/queries.py` and call it from a page with
`run(Q.MY_QUERY, params)`. Filters use `{where}` placeholders and named parameters (`:region`), never string concatenation of values.
Remember that SQLite divides integers as integers, so percentages are written `100.0 * a / NULLIF(b, 0)`.
Requires SQLite 3.25+ (window functions), which ships with any recent Python.

## Pages
- Executive Overview: filtered KPIs, monthly revenue, category mix, regional sales, top products, store performance, inventory alerts, insights and exports.
- Product Analytics: category, brand and product performance.
- Store & Regional Analytics: regional/store comparison and target achievement.
- Inventory Monitoring: reorder-level alerts and stock distribution.
- Campaign Insights: campaign register, budget and before/after indicators.

All financial amounts are shown in Algerian dinars (DZD / DA). The supplied dataset is synthetic and is intended for teaching and demonstration.

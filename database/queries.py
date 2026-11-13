"""All SQL used by the dashboard (SQLite dialect), in one place.

Conventions
-----------
* Queries are plain strings. `{where}` is replaced by a filter built with `scope_where()` (or a fixed clause).
* Values are always passed as named parameters (`:year`, `:region`...), never concatenated.
* SQLite divides integers as integers, so every ratio is written `100.0 * a / NULLIF(b, 0)`.
* Pages call them as  run(Q.EXEC_KPIS, params, where=W)  (see utils/dashboard.py).
"""

# ---------------------------------------------------------------- filters
def scope_where(quarter="All", month="All", region="All", store="All", dates=True):
    """WHERE-clause body + params for the executive filters (dates=False -> region/store only).
    `quarter` is "All" or "<year>-<Qn>", for example "2026-Q2"."""
    conds, p = ["1=1"], {}
    if region != "All": conds.append("Region = :region"); p["region"] = region
    if store != "All": conds.append("Store_Name = :store"); p["store"] = store
    if dates and quarter != "All":
        year, q = quarter.split("-")
        conds.append("Year = :year AND Quarter = :quarter"); p["year"] = int(year); p["quarter"] = q
    if dates and month != "All": conds.append("Month = :month"); p["month"] = int(month)
    return " AND ".join(conds), p


# Columns / tables allowed in DISTINCT_VALUES (identifiers cannot be bound as parameters)
_DISTINCT_OK = {"vw_clean_sales": {"Year", "Month", "Region", "Store_Name", "Category", "Brand"},
                "vw_inventory_status": {"Region"}}

# `{column}` and `{table}` are filled by distinct_query(), which checks them against the list above.
DISTINCT_VALUES = "SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL ORDER BY {column}"

def distinct_query(column, table="vw_clean_sales"):
    if column not in _DISTINCT_OK.get(table, ()):
        raise ValueError(f"distinct values not allowed for {table}.{column}")
    return DISTINCT_VALUES.format(column=column, table=table)


# ---------------------------------------------------------------- executive filters
QUARTERS = "SELECT DISTINCT Year, Quarter FROM vw_clean_sales ORDER BY Year, Quarter"

QUARTER_MONTHS = """
SELECT DISTINCT Month FROM vw_clean_sales
WHERE Year = :year AND Quarter = :quarter ORDER BY Month"""

ALL_MONTHS = "SELECT DISTINCT Month FROM vw_clean_sales ORDER BY Month"


# ---------------------------------------------------------------- home (app.py)
HOME_TOTALS = """
SELECT COUNT(*) AS records, COUNT(DISTINCT Store_ID) AS stores, COUNT(DISTINCT Product_ID) AS products
FROM vw_clean_sales"""


# ---------------------------------------------------------------- executive overview
EXEC_KPIS = """
SELECT SUM(Sales_Amount_DZD) AS revenue,
       SUM(Gross_Profit_DZD) AS profit,
       100.0 * SUM(Gross_Profit_DZD) / NULLIF(SUM(Sales_Amount_DZD), 0) AS margin,
       COUNT(DISTINCT Transaction_ID) AS transactions,
       SUM(Quantity_Sold) AS quantity
FROM vw_clean_sales WHERE {where}"""

EXEC_MONTHLY = """
SELECT Year, Month, SUBSTR(Month_Name, 1, 3) AS Mon, SUM(Sales_Amount_DZD) AS revenue
FROM vw_clean_sales WHERE {where}
GROUP BY Year, Month, Month_Name ORDER BY Year, Month"""

EXEC_CATEGORY = """
SELECT Category, SUM(Sales_Amount_DZD) AS revenue,
       100.0 * SUM(Sales_Amount_DZD) / SUM(SUM(Sales_Amount_DZD)) OVER () AS share
FROM vw_clean_sales WHERE {where}
GROUP BY Category ORDER BY revenue DESC"""

EXEC_REGION = """
SELECT Region, SUM(Sales_Amount_DZD) AS revenue
FROM vw_clean_sales WHERE {where}
GROUP BY Region ORDER BY revenue DESC"""

EXEC_TOP_PRODUCTS = """
SELECT Product_Name, SUM(Sales_Amount_DZD) AS revenue
FROM vw_clean_sales WHERE {where}
GROUP BY Product_Name ORDER BY revenue DESC LIMIT 10"""

EXEC_STORES = """
SELECT Store_Name, SUM(Sales_Amount_DZD) AS revenue
FROM vw_clean_sales WHERE {where}
GROUP BY Store_Name ORDER BY revenue DESC LIMIT 8"""

EXEC_INVENTORY_ALERTS = """
SELECT Product_Name AS Product, Store_Name AS Store, Stock_Quantity AS Stock, Reorder_Level AS "Reorder level", Status
FROM vw_inventory_status WHERE Status <> 'Normal' ORDER BY Stock_Quantity LIMIT 7"""

EXEC_EXPORT = """
SELECT * FROM vw_clean_sales WHERE {where} ORDER BY Order_Date, Transaction_ID"""

# Latest month in scope vs the previous calendar month (LAG). `{base_where}` = region/store filters only,
# so the previous month is found across years; `{where}` = full filters, to pick the latest month.
MONTH_COMPARISON = """
WITH m AS (
    SELECT Year*100+Month AS ym, SUM(Sales_Amount_DZD) AS revenue, SUM(Gross_Profit_DZD) AS profit,
           COUNT(DISTINCT Transaction_ID) AS transactions, SUM(Quantity_Sold) AS quantity
    FROM vw_clean_sales WHERE {base_where} GROUP BY Year*100+Month),
d AS (
    SELECT ym, revenue, profit, transactions, quantity,
           LAG(ym)           OVER w AS p_ym,
           LAG(revenue)      OVER w AS p_revenue,
           LAG(profit)       OVER w AS p_profit,
           LAG(transactions) OVER w AS p_transactions,
           LAG(quantity)     OVER w AS p_quantity
    FROM m WINDOW w AS (ORDER BY ym))
SELECT ym, p_ym,
       100.0 * (revenue - p_revenue)           / NULLIF(p_revenue, 0)      AS revenue,
       100.0 * (profit - p_profit)             / NULLIF(p_profit, 0)       AS profit,
       100.0 * (transactions - p_transactions) / NULLIF(p_transactions, 0) AS transactions,
       100.0 * (quantity - p_quantity)         / NULLIF(p_quantity, 0)     AS quantity,
       100.0 * profit / NULLIF(revenue, 0) - 100.0 * p_profit / NULLIF(p_revenue, 0) AS margin,
       (SELECT COUNT(DISTINCT Year*100+Month) FROM vw_clean_sales WHERE {where}) AS n_months
FROM d
WHERE ym = (SELECT MAX(Year*100+Month) FROM vw_clean_sales WHERE {where})
  AND p_ym = CASE WHEN ym % 100 = 1 THEN ym - 89 ELSE ym - 1 END"""


# ---------------------------------------------------------------- product analytics
# Filter used with list parameters: pass lists=("cats", "brands") to run().
PRODUCT_FILTER = "Category IN :cats AND Brand IN :brands"

PRODUCT_KPIS = """
SELECT COALESCE(SUM(Sales_Amount_DZD), 0) AS rev, COALESCE(SUM(Gross_Profit_DZD), 0) AS profit,
       COALESCE(SUM(Quantity_Sold), 0) AS qty
FROM vw_clean_sales WHERE {where}"""

PRODUCT_BY_CATEGORY = """
SELECT Category, SUM(Sales_Amount_DZD) AS revenue
FROM vw_clean_sales WHERE {where}
GROUP BY Category ORDER BY revenue DESC"""

PRODUCT_TOP = """
SELECT Product_Name, Category, SUM(Sales_Amount_DZD) AS revenue
FROM vw_clean_sales WHERE {where}
GROUP BY Product_Name, Category ORDER BY revenue DESC LIMIT 10"""

PRODUCT_DETAIL = """
SELECT Product_ID, Product_Name, Category, Brand,
       SUM(Sales_Amount_DZD) AS Revenue_DZD, SUM(Gross_Profit_DZD) AS Gross_Profit_DZD,
       SUM(Quantity_Sold) AS Quantity_Sold,
       ROUND(100.0 * SUM(Gross_Profit_DZD) / NULLIF(SUM(Sales_Amount_DZD), 0), 1) AS Gross_Margin_Pct
FROM vw_clean_sales WHERE {where}
GROUP BY Product_ID, Product_Name, Category, Brand ORDER BY Revenue_DZD DESC"""


# ---------------------------------------------------------------- store & regional analytics
# Use with lists=("regions",).
STORE_REGIONAL = """
SELECT Region, SUM(Sales_Amount_DZD) AS Revenue_DZD, SUM(Quantity_Sold) AS Quantity_Sold,
       COUNT(DISTINCT Transaction_ID) AS Transactions
FROM vw_clean_sales WHERE Region IN :regions
GROUP BY Region ORDER BY Region"""

STORE_BY_STORE = """
SELECT Store_ID, Store_Name, Region, SUM(Sales_Amount_DZD) AS Revenue_DZD, SUM(Quantity_Sold) AS Quantity_Sold,
       COUNT(DISTINCT Transaction_ID) AS Transactions
FROM vw_clean_sales WHERE Region IN :regions
GROUP BY Store_ID, Store_Name, Region ORDER BY Revenue_DZD"""

STORE_TARGETS = """
SELECT t.Store_ID, SUM(t.Target_Revenue_DZD) AS Target_Revenue_DZD, SUM(t.Actual_Sales_DZD) AS Actual_Sales_DZD,
       ROUND(100.0 * SUM(t.Actual_Sales_DZD) / NULLIF(SUM(t.Target_Revenue_DZD), 0), 1) AS Achievement_Rate_Pct,
       d.Store_Name, d.Region
FROM vw_target_performance t JOIN dim_store d ON d.Store_ID = t.Store_ID
WHERE d.Region IN :regions
GROUP BY t.Store_ID, d.Store_Name, d.Region ORDER BY Achievement_Rate_Pct DESC"""


# ---------------------------------------------------------------- inventory monitoring
INV_TOTALS = """
SELECT COUNT(*) AS total,
       COALESCE(SUM(Status = 'Below threshold'), 0) AS below,
       COALESCE(SUM(Status <> 'Normal'), 0) AS monitor
FROM vw_inventory_status"""

INV_STOCK_BY_CATEGORY = """
SELECT Category, SUM(Stock_Quantity) AS stock
FROM vw_inventory_status GROUP BY Category ORDER BY Category"""

INV_STATUS_COUNTS = """
SELECT Status, COUNT(*) AS items
FROM vw_inventory_status GROUP BY Status ORDER BY items DESC"""

INV_ALERTS = """
SELECT Product_Name AS Product, Category, Store_Name AS Store, Region,
       Stock_Quantity AS "Current stock", Reorder_Level AS "Reorder level", Status
FROM vw_inventory_status
WHERE Status <> 'Normal' AND (:region = 'All' OR Region = :region)
ORDER BY Stock_Quantity"""


# ---------------------------------------------------------------- campaign insights
CAMPAIGNS = "SELECT * FROM marketing_campaigns ORDER BY Campaign_ID"

CAMPAIGN_TOTALS = """
SELECT COUNT(*) AS n, COALESCE(SUM(Campaign_Budget_DZD), 0) AS budget FROM marketing_campaigns"""

CAMPAIGN_BEFORE_AFTER = """
SELECT KPI, Before_Campaign, After_Campaign, Unit, After_Campaign - Before_Campaign AS "Change",
       ROUND(100.0 * (After_Campaign - Before_Campaign) / NULLIF(Before_Campaign, 0), 1) AS Change_Pct
FROM before_after_campaign ORDER BY KPI"""

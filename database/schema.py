"""SQLite star schema (DDL) for the ABC Retail data warehouse. Executed by database/etl_load.py.

SQLite notes: integer / integer is an INTEGER division, so every percentage below is written as
100.0 * numerator / denominator. Dates are stored as ISO text (YYYY-MM-DD).
"""

SCHEMA_SQL = """
PRAGMA foreign_keys = OFF;
DROP VIEW  IF EXISTS vw_monthly_kpis;
DROP VIEW  IF EXISTS vw_inventory_status;
DROP VIEW  IF EXISTS vw_target_performance;
DROP VIEW  IF EXISTS vw_clean_sales;
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS sales_targets;
DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS marketing_campaigns;
DROP TABLE IF EXISTS before_after_campaign;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_store;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_time;
PRAGMA foreign_keys = ON;

-- ---------- Dimensions ----------
CREATE TABLE dim_product (
    Product_Key    INTEGER PRIMARY KEY,
    Product_ID     TEXT    NOT NULL UNIQUE,
    Product_Name   TEXT    NOT NULL,
    Category       TEXT    NOT NULL,
    Brand          TEXT    NOT NULL,
    Product_Type   TEXT,
    Unit_Cost_DZD  INTEGER,
    List_Price_DZD INTEGER
);

CREATE TABLE dim_store (
    Store_Key       INTEGER PRIMARY KEY,
    Store_ID        TEXT    NOT NULL UNIQUE,
    Store_Name      TEXT    NOT NULL,
    City            TEXT    NOT NULL,
    Department_Code INTEGER,
    Region          TEXT    NOT NULL
);

CREATE TABLE dim_customer (
    Customer_Key     INTEGER PRIMARY KEY,
    Customer_ID      TEXT    NOT NULL UNIQUE,
    Customer_Name    TEXT,
    Gender           TEXT,
    City             TEXT,
    Customer_Segment TEXT
);

CREATE TABLE dim_time (
    Time_Key   INTEGER PRIMARY KEY,          -- YYYYMMDD
    Date       TEXT    NOT NULL UNIQUE,      -- ISO date
    Day        INTEGER NOT NULL,
    Month      INTEGER NOT NULL,
    Month_Name TEXT    NOT NULL,
    Quarter    TEXT    NOT NULL,
    Year       INTEGER NOT NULL
);

-- ---------- Fact ----------
CREATE TABLE fact_sales (
    Transaction_ID      TEXT    NOT NULL PRIMARY KEY,
    Product_Key         INTEGER NOT NULL REFERENCES dim_product  (Product_Key),
    Store_Key           INTEGER NOT NULL REFERENCES dim_store    (Store_Key),
    Customer_Key        INTEGER NOT NULL REFERENCES dim_customer (Customer_Key),
    Date_Key            INTEGER NOT NULL REFERENCES dim_time     (Time_Key),
    Quantity_Sold       INTEGER NOT NULL,
    Unit_Price_DZD      INTEGER NOT NULL,
    Sales_Amount_DZD    INTEGER NOT NULL,
    Discount_Amount_DZD INTEGER NOT NULL DEFAULT 0,
    Cost_Amount_DZD     INTEGER NOT NULL,
    Gross_Profit_DZD    INTEGER NOT NULL
);
CREATE INDEX idx_fact_date    ON fact_sales (Date_Key);
CREATE INDEX idx_fact_store   ON fact_sales (Store_Key);
CREATE INDEX idx_fact_product ON fact_sales (Product_Key);

-- ---------- Other tables ----------
CREATE TABLE sales_targets (
    Target_ID          TEXT    NOT NULL PRIMARY KEY,
    Year               INTEGER NOT NULL,
    Month              INTEGER NOT NULL,
    Store_ID           TEXT    NOT NULL REFERENCES dim_store (Store_ID),
    Target_Revenue_DZD INTEGER NOT NULL
);

CREATE TABLE inventory (
    Store_ID       TEXT    NOT NULL REFERENCES dim_store   (Store_ID),
    Product_ID     TEXT    NOT NULL REFERENCES dim_product (Product_ID),
    Stock_Quantity INTEGER NOT NULL,
    Reorder_Level  INTEGER NOT NULL,
    Snapshot_Date  TEXT    NOT NULL,
    Currency       TEXT,
    PRIMARY KEY (Store_ID, Product_ID, Snapshot_Date)
);

CREATE TABLE marketing_campaigns (
    Campaign_ID         TEXT NOT NULL PRIMARY KEY,
    Campaign_Name       TEXT NOT NULL,
    Product_ID          TEXT,
    Store_ID            TEXT,
    Start_Date          TEXT,
    End_Date            TEXT,
    Campaign_Budget_DZD INTEGER
);

CREATE TABLE before_after_campaign (
    KPI             TEXT NOT NULL PRIMARY KEY,
    Before_Campaign INTEGER,
    After_Campaign  INTEGER,
    Unit            TEXT
);

-- ---------- Views used by the dashboard ----------
-- Denormalised sales (same columns as the Excel sheet Clean_Sales)
CREATE VIEW vw_clean_sales AS
SELECT f.Transaction_ID,
       t.Date AS Order_Date, t.Year, t.Month, t.Month_Name, t.Quarter,
       s.Store_ID, s.Store_Name, s.City, s.Region,
       p.Product_ID, p.Product_Name, p.Category, p.Brand,
       c.Customer_ID, c.Customer_Segment,
       f.Quantity_Sold, f.Unit_Price_DZD, f.Discount_Amount_DZD,
       f.Sales_Amount_DZD, f.Cost_Amount_DZD, f.Gross_Profit_DZD
FROM fact_sales f
JOIN dim_time     t ON t.Time_Key     = f.Date_Key
JOIN dim_store    s ON s.Store_Key    = f.Store_Key
JOIN dim_product  p ON p.Product_Key  = f.Product_Key
JOIN dim_customer c ON c.Customer_Key = f.Customer_Key;

-- Target vs actual, computed in SQL
CREATE VIEW vw_target_performance AS
SELECT g.Target_ID, g.Year, g.Month, g.Store_ID, g.Target_Revenue_DZD,
       COALESCE(a.Actual_Sales_DZD, 0) AS Actual_Sales_DZD,
       100.0 * COALESCE(a.Actual_Sales_DZD, 0) / g.Target_Revenue_DZD AS Achievement_Rate_Pct
FROM sales_targets g
LEFT JOIN (SELECT Year, Month, Store_ID, SUM(Sales_Amount_DZD) AS Actual_Sales_DZD
           FROM vw_clean_sales GROUP BY Year, Month, Store_ID) a
       ON a.Year = g.Year AND a.Month = g.Month AND a.Store_ID = g.Store_ID;

-- Month-over-month KPIs using window functions (for reporting / validation)
CREATE VIEW vw_monthly_kpis AS
SELECT Year, Month, Revenue, Gross_Profit, Transactions, Quantity,
       100.0 * Gross_Profit / Revenue                                                    AS Gross_Margin_Pct,
       100.0 * (Revenue - LAG(Revenue) OVER w) / LAG(Revenue) OVER w                     AS Revenue_MoM_Pct,
       100.0 * (Gross_Profit - LAG(Gross_Profit) OVER w) / LAG(Gross_Profit) OVER w       AS Profit_MoM_Pct,
       100.0 * (Transactions - LAG(Transactions) OVER w) / LAG(Transactions) OVER w       AS Transactions_MoM_Pct,
       100.0 * (Quantity - LAG(Quantity) OVER w) / LAG(Quantity) OVER w                   AS Quantity_MoM_Pct
FROM (SELECT Year, Month, SUM(Sales_Amount_DZD) AS Revenue, SUM(Gross_Profit_DZD) AS Gross_Profit,
             COUNT(DISTINCT Transaction_ID) AS Transactions, SUM(Quantity_Sold) AS Quantity
      FROM vw_clean_sales GROUP BY Year, Month) m
WINDOW w AS (ORDER BY Year, Month);

-- Inventory with product/store names and reorder status (latest snapshot only)
CREATE VIEW vw_inventory_status AS
SELECT i.Store_ID, s.Store_Name, s.Region, i.Product_ID, p.Product_Name, p.Category,
       i.Stock_Quantity, i.Reorder_Level, i.Snapshot_Date,
       CASE WHEN i.Stock_Quantity < i.Reorder_Level         THEN 'Below threshold'
            WHEN i.Stock_Quantity <= i.Reorder_Level * 1.15 THEN 'Watch'
            ELSE 'Normal' END AS Status
FROM inventory i
JOIN dim_store   s ON s.Store_ID   = i.Store_ID
JOIN dim_product p ON p.Product_ID = i.Product_ID
WHERE i.Snapshot_Date = (SELECT MAX(Snapshot_Date) FROM inventory);
"""

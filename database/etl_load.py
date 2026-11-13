"""Load the Excel workbook into the SQLite star schema (openpyxl + sqlite3, no pandas).

Usage:  python database/etl_load.py
Drops and rebuilds every table in data/abc_retail.db (override the path with ABC_DB_PATH).
"""
import sys
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from database.connection import DB_PATH, connect  # noqa: E402
from database.schema import SCHEMA_SQL  # noqa: E402

XLSX = ROOT / "ABC_Retail_BI_Synthetic_Datasets.xlsx"


def read_sheet(wb, name):
    rows = wb[name].iter_rows(values_only=True)
    header = next(rows)
    return [dict(zip(header, r)) for r in rows if any(v is not None for v in r)]


def insert(conn, table, rows, columns=None, quiet=False):
    columns = columns or list(rows[0].keys())
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(':' + c for c in columns)})"
    conn.executemany(sql, [{c: r[c] for c in columns} for r in rows])
    if not quiet:
        print(f"loaded {table:<22} {len(rows):>6} rows")


def build_database(quiet=False):
    """Create the schema and load all tables. Returns the number of rows in vw_clean_sales."""
    wb = load_workbook(XLSX, read_only=True, data_only=True)
    unit_price = {r["Transaction_ID"]: r["Unit_Price_DZD"] for r in read_sheet(wb, "Clean_Sales")}  # only in the flat sheet
    fact = read_sheet(wb, "Fact_Sales")
    for r in fact:
        r["Unit_Price_DZD"] = unit_price[r["Transaction_ID"]]

    conn = connect(read_only=False)
    try:
        with conn:                                          # one transaction: all or nothing
            conn.executescript(SCHEMA_SQL)                  # drops and recreates everything
            q = dict(quiet=quiet)
            insert(conn, "dim_product", read_sheet(wb, "Dim_Product"), **q)
            insert(conn, "dim_store", read_sheet(wb, "Dim_Store"), **q)
            insert(conn, "dim_customer", read_sheet(wb, "Dim_Customer"), **q)
            insert(conn, "dim_time", read_sheet(wb, "Dim_Time"), **q)
            insert(conn, "fact_sales", fact, ["Transaction_ID", "Product_Key", "Store_Key", "Customer_Key", "Date_Key",
                                              "Quantity_Sold", "Unit_Price_DZD", "Sales_Amount_DZD", "Discount_Amount_DZD",
                                              "Cost_Amount_DZD", "Gross_Profit_DZD"], **q)
            insert(conn, "sales_targets", read_sheet(wb, "Sales_Targets"), **q)
            insert(conn, "inventory", read_sheet(wb, "Inventory"), **q)
            insert(conn, "marketing_campaigns", read_sheet(wb, "Marketing_Campaigns"), **q)
            insert(conn, "before_after_campaign", read_sheet(wb, "Before_After_Campaign"), **q)
        n = conn.execute("SELECT COUNT(*) FROM vw_clean_sales").fetchone()[0]
    finally:
        conn.close()
    if not quiet:
        print("vw_clean_sales rows:", n)
        print("database file:", DB_PATH)
    return n


if __name__ == "__main__":
    build_database()

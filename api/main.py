
from pathlib import Path

import duckdb
import pandas as pd
from fastapi import FastAPI, HTTPException, Query

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent

PARQUET_PATH = (
    BASE_DIR / "data" / "processed" / "online_retail_cleaned.parquet"
)

RFM_PATH = BASE_DIR / "data" / "processed" / "customer_rfm.csv"

app = FastAPI(
    title="RevenueLeak API",
    description="Retail Revenue Intelligence and Analytics API",
    version="1.0.0"
)


# Database helper
def run_query(sql, params=None):
    if not PARQUET_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail="Cleaned Parquet dataset not found."
        )

    con = duckdb.connect(database=":memory:")

    try:
        df = con.execute(
            sql,
            params or []
        ).fetchdf()

        # Replace NaN and infinity with JSON-compatible values.
        return df.astype(object).where(pd.notna(df), None).to_dict(
            orient="records"
        )
    finally:
        con.close()


def country_filter(country):
    if country:
        return "WHERE Country = ?", [country]

    return "", []


@app.get("/")
def home():
    return {
        "message": "Welcome to RevenueLeak API",
        "version": "1.0.0",
        "documentation": "/docs"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "RevenueLeak API"
    }


@app.get("/api/overview")
def get_overview(
    country: str | None = Query(default=None)
):
    where, params = country_filter(country)

    sql = f"""
        SELECT
            ROUND(SUM(SalesValue), 2) AS total_sales,
            ROUND(SUM(CancellationValue), 2) AS cancellation_value,
            ROUND(SUM(NetGrossRevenue), 2) AS net_gross_revenue,

            COUNT(DISTINCT CASE
                WHEN IsCancellation = FALSE AND SalesValue > 0
                THEN Invoice
            END) AS sales_invoices

        FROM read_parquet(?)
        {where}
    """

    return run_query(sql, [str(PARQUET_PATH), *params])[0]


@app.get("/api/monthly-revenue")
def get_monthly_revenue(
    country: str | None = Query(default=None)
):
    where, params = country_filter(country)

    sql = f"""
        SELECT
            STRFTIME(InvoiceDate, '%Y-%m') AS month,
            ROUND(SUM(SalesValue), 2) AS sales,
            ROUND(SUM(CancellationValue), 2) AS cancellations,
            ROUND(SUM(NetGrossRevenue), 2) AS net_gross_revenue

        FROM read_parquet(?)
        {where}
        GROUP BY month
        ORDER BY month
    """

    return run_query(sql, [str(PARQUET_PATH), *params])


@app.get("/api/countries")
def get_countries():
    sql = """
        SELECT
            Country,
            ROUND(SUM(SalesValue), 2) AS total_sales,
            ROUND(SUM(CancellationValue), 2) AS cancellation_value,
            ROUND(SUM(NetGrossRevenue), 2) AS net_gross_revenue

        FROM read_parquet(?)
        GROUP BY Country
        ORDER BY net_gross_revenue DESC
    """

    return run_query(sql, [str(PARQUET_PATH)])


@app.get("/api/products/top")
def get_top_products(
    limit: int = Query(default=10, ge=1, le=100),
    country: str | None = Query(default=None)
):
    where, params = country_filter(country)

    sql = f"""
        SELECT
            Description AS product,
            ROUND(SUM(SalesValue), 2) AS sales_value,
            SUM(Quantity) AS quantity_sold

        FROM read_parquet(?)
        {where}
        {"AND" if where else "WHERE"} SalesValue > 0
        GROUP BY Description
        ORDER BY sales_value DESC
        LIMIT ?
    """

    return run_query(
        sql,
        [str(PARQUET_PATH), *params, limit]
    )


@app.get("/api/products/cancellations")
def get_cancelled_products(
    limit: int = Query(default=10, ge=1, le=100),
    country: str | None = Query(default=None)
):
    where, params = country_filter(country)

    sql = f"""
        SELECT
            Description AS product,
            ROUND(SUM(CancellationValue), 2) AS cancellation_value,
            SUM(ABS(Quantity)) AS cancelled_quantity

        FROM read_parquet(?)
        {where}
        {"AND" if where else "WHERE"} CancellationValue > 0
        GROUP BY Description
        ORDER BY cancellation_value DESC
        LIMIT ?
    """

    return run_query(
        sql,
        [str(PARQUET_PATH), *params, limit]
    )


@app.get("/api/customers/segments")
def get_customer_segments():
    if not RFM_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail="RFM CSV not found. Run scripts/analyze_rfm.py first."
        )

    df = pd.read_csv(RFM_PATH)

    return (
        df["segment"]
        .value_counts()
        .rename_axis("segment")
        .reset_index(name="customers")
        .to_dict(orient="records")
    )


@app.get("/api/customers/top")
def get_top_customers(
    limit: int = Query(default=10, ge=1, le=100)
):
    if not RFM_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail="RFM CSV not found. Run scripts/analyze_rfm.py first."
        )

    df = pd.read_csv(RFM_PATH)

    result = df.sort_values(
        "monetary",
        ascending=False
    ).head(limit)

    return result.to_dict(orient="records")

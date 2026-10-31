
import duckdb

PARQUET_PATH = "data/processed/online_retail_cleaned.parquet"

# Create an in-memory DuckDB connection
con = duckdb.connect(database=":memory:")

# Query the Parquet file directly
query = f"""
    SELECT
        COUNT(*) AS total_rows,
        COUNT(DISTINCT Invoice) AS unique_invoices,
        COUNT(DISTINCT Country) AS total_countries,
        ROUND(SUM(NetGrossRevenue), 2) AS gross_revenue
    FROM read_parquet('{PARQUET_PATH}')
"""

result = con.execute(query).fetchdf()

print("DuckDB Dataset Summary:")
print(result)

# Monthly revenue analysis
monthly_query = f"""
    SELECT
        STRFTIME(InvoiceDate, '%Y-%m') AS month,
        ROUND(SUM(NetGrossRevenue), 2) AS gross_revenue
    FROM read_parquet('{PARQUET_PATH}')
    GROUP BY month
    ORDER BY month
"""

monthly_result = con.execute(monthly_query).fetchdf()

print("\nMonthly Gross Revenue:")
print(monthly_result.head(12))


# Monthly revenue by country
country_query = f"""
    SELECT
        Country,
        STRFTIME(InvoiceDate, '%Y-%m') AS month,
        ROUND(SUM(NetGrossRevenue), 2) AS gross_revenue
    FROM read_parquet('{PARQUET_PATH}')
    GROUP BY Country, month
    ORDER BY Country, month
"""

country_result = con.execute(country_query).fetchdf()

print("\nMonthly Revenue by Country:")
print(country_result.head(20))

print("\nTop 10 Countries by Gross Revenue:")

top_countries_query = f"""
    SELECT
        Country,
        ROUND(SUM(NetGrossRevenue), 2) AS gross_revenue
    FROM read_parquet('{PARQUET_PATH}')
    GROUP BY Country
    ORDER BY gross_revenue DESC
    LIMIT 10
"""

print(con.execute(top_countries_query).fetchdf())



cancellation_country_query = f"""
    SELECT
        Country,
        ROUND(SUM(SalesValue), 2) AS total_sales,
        ROUND(SUM(CancellationValue), 2) AS cancellation_value,
        ROUND(SUM(NetGrossRevenue), 2) AS net_gross_revenue,
        ROUND(
            100.0 * SUM(CancellationValue)
            / NULLIF(SUM(SalesValue), 0),
            2
        ) AS cancellation_rate_pct
    FROM read_parquet('{PARQUET_PATH}')
    GROUP BY Country
    ORDER BY cancellation_value DESC
    LIMIT 10
"""

print("\nTop 10 Countries by Cancellation Value:")
print(
    con.execute(cancellation_country_query).fetchdf()
)


volume_query = f"""
    SELECT
        Country,

        COUNT(DISTINCT CASE
            WHEN Quantity > 0 AND NOT IsCancellation
            THEN Invoice
        END) AS sales_invoices,

        COUNT(DISTINCT CASE
            WHEN IsCancellation
            THEN Invoice
        END) AS cancellation_invoices,

        ROUND(SUM(SalesValue), 2) AS total_sales,

        ROUND(SUM(CancellationValue), 2) AS cancellation_value,

        ROUND(
            100.0 * SUM(CancellationValue)
            / NULLIF(SUM(SalesValue), 0),
            2
        ) AS cancellation_rate_pct

    FROM read_parquet('{PARQUET_PATH}')
    GROUP BY Country
    ORDER BY cancellation_rate_pct DESC
"""

print("\nCancellation Volume by Country:")

print(
    con.execute(volume_query).fetchdf().to_string(index=False)
)


con.close()

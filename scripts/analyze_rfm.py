import duckdb
import pandas as pd

PARQUET_PATH = "data/processed/online_retail_cleaned.parquet"
OUTPUT_PATH = "data/processed/customer_rfm.csv"

con = duckdb.connect(database=":memory:")

query = f"""
WITH analysis_date AS (
    SELECT MAX(CAST(InvoiceDate AS DATE)) + INTERVAL 1 DAY AS date
    FROM read_parquet('{PARQUET_PATH}')
)

SELECT
    "Customer ID" AS customer_id,

    DATE_DIFF(
        'day',
        CAST(MAX(InvoiceDate) AS DATE),
        (SELECT date FROM analysis_date)
    ) AS recency,

    COUNT(DISTINCT Invoice) AS frequency,

    ROUND(SUM(SalesValue), 2) AS monetary

FROM read_parquet('{PARQUET_PATH}')

WHERE
    "Customer ID" IS NOT NULL
    AND SalesValue > 0
    AND IsCancellation = FALSE

GROUP BY "Customer ID"
"""

df = con.execute(query).fetchdf()
con.close()

# Calculate RFM scores from 1 to 5.
# Lower recency is better, so reverse its ranking.
df["R_score"] = pd.qcut(
    df["recency"].rank(method="first", ascending=False),
    5,
    labels=[1, 2, 3, 4, 5]
).astype(int)

df["F_score"] = pd.qcut(
    df["frequency"].rank(method="first"),
    5,
    labels=[1, 2, 3, 4, 5]
).astype(int)

df["M_score"] = pd.qcut(
    df["monetary"].rank(method="first"),
    5,
    labels=[1, 2, 3, 4, 5]
).astype(int)

# Assign customer segments.
def assign_segment(row):
    r = row["R_score"]
    f = row["F_score"]
    m = row["M_score"]

    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    elif f >= 4 and r >= 3:
        return "Loyal Customers"
    elif r >= 4 and f <= 2:
        return "New Customers"
    elif r <= 2 and f >= 3:
        return "At Risk"
    elif r <= 2 and f <= 2:
        return "Hibernating"
    elif m >= 4:
        return "Big Spenders"
    else:
        return "Others"


df["segment"] = df.apply(assign_segment, axis=1)

# Save customer-level results.
df.to_csv(OUTPUT_PATH, index=False)

print("\nCustomer Segment Counts:")
print(df["segment"].value_counts().to_string())

print("\nTop 10 Customers:")
print(
    df.sort_values("monetary", ascending=False)
    .head(10)
    .to_string(index=False)
)

print(f"\nTotal customers analyzed: {len(df)}")
print(f"RFM results saved to: {OUTPUT_PATH}")
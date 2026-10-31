
import pandas as pd
from pathlib import Path

DATA_PATH = Path("data/raw/online_retail_II.csv")

df = pd.read_csv(
    DATA_PATH,
    encoding="ISO-8859-1"
)

df["Invoice"] = df["Invoice"].astype("string").str.strip()
df["IsCancellation"] = df["Invoice"].str.startswith("C", na=False)

# Identify negative quantities before cleaning
negative_rows = df[df["Quantity"] < 0].copy()

# Separate cancellation and non-cancellation transactions
other_negative = negative_rows[
    ~negative_rows["IsCancellation"]
].copy()

print("Total negative quantity rows:", len(negative_rows))
print("Negative quantity rows with C invoice:",
      negative_rows["IsCancellation"].sum())
print("Negative quantity rows without C invoice:",
      len(other_negative))

print("\nPrice analysis of negative quantities without C invoice:")

print(
    other_negative["Price"]
    .apply(lambda x: "Positive" if x > 0 else "Zero or Negative")
    .value_counts()
)

print("\nSample of negative quantities without C invoice:")
print(
    other_negative[
        ["Invoice", "StockCode", "Description",
         "Quantity", "Price", "InvoiceDate", "Customer ID"]
    ].head(10)
)

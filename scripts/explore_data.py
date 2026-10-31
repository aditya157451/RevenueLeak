
import pandas as pd
from pathlib import Path

# Dataset location
DATA_PATH = Path("data/raw/online_retail_II.csv")

# Load CSV dataset
df = pd.read_csv(DATA_PATH, encoding="ISO-8859-1")

print("Dataset loaded successfully!")

print("\nFirst 5 rows:")
print(df.head())

print("\nDataset shape:")
print(df.shape)

print("\nColumn information:")
df.info()

print("\nMissing values:")
print(df.isnull().sum())

print("\nDuplicate rows:")
print(df.duplicated().sum())

print("\nExploration completed!")


print("\n========== TRANSACTION ANALYSIS ==========")

# 1. Identify cancellation invoices
invoice = df["Invoice"].astype("string").str.strip()

cancellation_mask = invoice.str.startswith("C", na=False)

print("\nCancellation analysis:")
print("Cancellation rows:", cancellation_mask.sum())
print("Unique cancellation invoices:",
      invoice[cancellation_mask].nunique())

# 2. Identify negative quantities
negative_quantity = df["Quantity"] < 0

print("\nNegative quantity rows:", negative_quantity.sum())

# 3. Identify invalid prices
invalid_price = df["Price"] <= 0

print("\nZero or negative price rows:", invalid_price.sum())

# 4. Convert InvoiceDate into datetime
df["InvoiceDate"] = pd.to_datetime(
    df["InvoiceDate"],
    dayfirst=True,
    errors="coerce"
)

print("\nDate analysis:")
print("Minimum date:", df["InvoiceDate"].min())
print("Maximum date:", df["InvoiceDate"].max())
print("Invalid dates:", df["InvoiceDate"].isna().sum())

# 5. Unique customers, invoices and countries
print("\nUnique records:")
print("Customers:", df["Customer ID"].nunique())
print("Invoices:", df["Invoice"].nunique())
print("Countries:", df["Country"].nunique())

# 6. Calculate duplicate percentage
duplicate_percentage = (
    df.duplicated().sum() / len(df)
) * 100

print("\nDuplicate percentage:",
      round(duplicate_percentage, 2), "%")

print("\n========== ANALYSIS COMPLETED ==========")

print("\nOriginal date examples:")
print(df["InvoiceDate"].head(10))

# Reload original data
df = pd.read_csv(
    DATA_PATH,
    encoding="ISO-8859-1"
)

# Inspect original date values
print("\nOriginal date examples:")
print(df["InvoiceDate"].head(10).to_list())

# Try mixed-format parsing
parsed_dates = pd.to_datetime(
    df["InvoiceDate"],
    format="mixed",
    dayfirst=False,
    errors="coerce"
)

print("\nCorrected date analysis:")
print("Minimum:", parsed_dates.min())
print("Maximum:", parsed_dates.max())
print("Invalid dates:", parsed_dates.isna().sum())

# Show examples of dates that failed
print("\nInvalid date examples:")
print(df.loc[parsed_dates.isna(), "InvoiceDate"].head(10))

invoice = df["Invoice"].astype("string").str.strip()

cancellation_mask = invoice.str.startswith("C", na=False)
negative_quantity_mask = df["Quantity"] < 0

print("Cancellation with negative quantity:",
      (cancellation_mask & negative_quantity_mask).sum())

print("Negative quantity without C invoice:",
      (~cancellation_mask & negative_quantity_mask).sum())

print("Cancellation with positive quantity:",
      (cancellation_mask & ~negative_quantity_mask).sum())
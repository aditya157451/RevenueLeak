import pandas as pd
from pathlib import Path

FILE_PATH = Path("data/processed/online_retail_cleaned.parquet")

df = pd.read_parquet(FILE_PATH)

print("Parquet file loaded successfully!")
print("Dataset shape:", df.shape)

print("\nColumns:")
print(df.columns.tolist())

print("\nFirst 5 rows:")
print(df.head())

print("\nGross Revenue:")
print(round(df["NetGrossRevenue"].sum(), 2))
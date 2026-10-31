
import pandas as pd
from pathlib import Path


def load_data(file_path):
    """
    Load Online Retail II CSV dataset.
    """
    df = pd.read_csv(
        file_path,
        encoding="ISO-8859-1"
    )

    return df


def clean_data(df):
    """
    Clean and prepare retail transaction data.
    """

    # Keep original raw data unchanged
    df = df.copy()

    # 1. Standardize column names
    df.columns = df.columns.str.strip()

    # 2. Remove leading/trailing spaces from text columns
    for col in ["Invoice", "StockCode", "Description", "Country"]:
        df[col] = df[col].astype("string").str.strip()

    # 3. Convert date column
    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"],
        format="mixed",
        dayfirst=False,
        errors="coerce"
    )

    # 4. Convert Customer ID to nullable integer
    df["Customer ID"] = pd.to_numeric(
        df["Customer ID"],
        errors="coerce"
    ).astype("Int64")

    # 5. Remove exact duplicate rows
    original_rows = len(df)
    df = df.drop_duplicates().copy()
    duplicates_removed = original_rows - len(df)

    # 6. Identify cancellation invoices
    df["IsCancellation"] = (
        df["Invoice"].str.startswith("C", na=False)
    )

    # 7. Identify valid prices
    df["IsValidPrice"] = df["Price"] > 0

    # 8. Track invalid dates and non-positive prices
    invalid_date_rows = df["InvoiceDate"].isna().sum()
    invalid_price_rows = (df["Price"] <= 0).sum()

    # Identify operational adjustment records
    excluded_negative_adjustments = (
        (df["Quantity"] < 0) &
        (df["Price"] <= 0) &
        (~df["IsCancellation"])
    ).sum()

    # Remove invalid dates and non-positive prices
    df = df[
        df["InvoiceDate"].notna() &
        df["IsValidPrice"]
    ].copy()

    print("Invalid date rows:", invalid_date_rows)
    print("Non-positive price rows:", invalid_price_rows)
    print(
        "Excluded non-C negative adjustments:",
        excluded_negative_adjustments
    )

    # 9. Calculate transaction line value
    df["LineValue"] = df["Quantity"] * df["Price"]

    # 10. Identify negative quantity transactions
    df["IsNegativeQuantity"] = df["Quantity"] < 0

    # 11. Calculate normal positive sales
    df["SalesValue"] = 0.0

    sales_mask = (
        ~df["IsCancellation"] &
        (df["Quantity"] > 0)
    )

    df.loc[sales_mask, "SalesValue"] = (
        df.loc[sales_mask, "LineValue"]
    )

    # 12. Calculate cancellation values
    df["CancellationValue"] = 0.0

    cancellation_mask = (
        df["IsCancellation"] &
        (df["Quantity"] < 0)
    )

    df.loc[cancellation_mask, "CancellationValue"] = (
        df.loc[cancellation_mask, "LineValue"].abs()
    )

    # 13. Identify other negative quantities separately
    df["OtherNegativeValue"] = 0.0

    other_returns = (
        ~df["IsCancellation"] &
        (df["Quantity"] < 0)
    )

    df.loc[other_returns, "OtherNegativeValue"] = (
        df.loc[other_returns, "LineValue"].abs()
    )

    # 14. Identify unusual positive quantities in cancellation invoices
    df["UnclassifiedCancellationValue"] = 0.0

    unusual_cancellation = (
        df["IsCancellation"] &
        (df["Quantity"] > 0)
    )

    df.loc[unusual_cancellation, "UnclassifiedCancellationValue"] = (
        df.loc[unusual_cancellation, "LineValue"]
    )

    # 15. Calculate preliminary net gross revenue
    # Other negative quantities are kept separate pending investigation.
    df["NetGrossRevenue"] = (
        df["SalesValue"] - df["CancellationValue"]
    )

    # 16. Display cleaning summary
    print("Cleaning completed!")
    print("Original rows:", original_rows)
    print("Duplicates removed:", duplicates_removed)
    print("Remaining rows:", len(df))
    print("Normal sales rows:", sales_mask.sum())
    print("Cancellation rows:", cancellation_mask.sum())
    print("Other negative quantity rows:", other_returns.sum())
    print("Unusual cancellation rows:", unusual_cancellation.sum())

    print("\nRevenue Summary:")
    print("Total Sales Value:", round(df["SalesValue"].sum(), 2))
    print("Cancellation Value:", round(df["CancellationValue"].sum(), 2))
    print("Other Negative Value:", round(df["OtherNegativeValue"].sum(), 2))
    print(
        "Preliminary Net Gross Revenue:",
        round(df["NetGrossRevenue"].sum(), 2)
    )
    print(
    "Rows with missing Customer ID:",
    df["Customer ID"].isna().sum()
)

    print(
        "Revenue from rows with missing Customer ID:",
        round(
            df.loc[
                df["Customer ID"].isna(),
                "NetGrossRevenue"
            ].sum(),
            2
        )
    )

    return df


if __name__ == "__main__":

    DATA_PATH = Path("data/raw/online_retail_II.csv")

    df = load_data(DATA_PATH)

    cleaned_df = clean_data(df)
    # Save cleaned dataset in Parquet format
    OUTPUT_PATH = Path("data/processed/online_retail_cleaned.parquet")

    cleaned_df.to_parquet(
        OUTPUT_PATH,
        engine="pyarrow",
        index=False
    )

    print("\nCleaned dataset saved successfully!")
    print("Saved at:", OUTPUT_PATH)
    print("File size (MB):", round(OUTPUT_PATH.stat().st_size / (1024 * 1024), 2))

    print("\nCleaned dataset preview:")
    print(cleaned_df.head())

    print("\nTotal cancellation invoice rows:",
          cleaned_df["IsCancellation"].sum())

    print("\nFinal columns:")
    print(cleaned_df.columns.tolist())

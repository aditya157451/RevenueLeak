
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from mlxtend.frequent_patterns import fpgrowth, association_rules


BASE_DIR = Path(__file__).resolve().parent.parent

PARQUET_PATH = BASE_DIR / "data" / "processed" / "online_retail_cleaned.parquet"
OUTPUT_DIR = BASE_DIR / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MIN_SUPPORT = 0.01
MIN_CONFIDENCE = 0.20
TOP_PRODUCTS = 500
MIN_INVOICE_COUNT = 20


def load_basket_data():
    """Load valid sales and prepare unique invoice-product pairs."""

    con = duckdb.connect(database=":memory:")

    query = """
        SELECT
            Invoice,
            StockCode,
            MAX(Description) AS Description
        FROM read_parquet(?)
        WHERE
            IsCancellation = FALSE
            AND Quantity > 0
            AND SalesValue > 0
            AND Invoice IS NOT NULL
            AND StockCode IS NOT NULL
        GROUP BY Invoice, StockCode
    """

    df = con.execute(query, [str(PARQUET_PATH)]).fetchdf()
    con.close()

    return df


def readable_items(items, descriptions):
    """Convert product codes into readable product names."""

    result = []

    for code in sorted(items):
        description = descriptions.get(code, "Unknown product")
        result.append(f"{code}: {description}")

    return " | ".join(result)


def run_market_basket_analysis():

    print("Loading transaction data...")

    df = load_basket_data()

    print(f"Invoice-product combinations: {len(df):,}")
    print(f"Unique invoices: {df['Invoice'].nunique():,}")
    print(f"Unique products: {df['StockCode'].nunique():,}")

    # Keep the most frequently purchased products
    product_frequency = df["StockCode"].value_counts()

    selected_products = product_frequency[
        product_frequency >= MIN_INVOICE_COUNT
    ].head(TOP_PRODUCTS).index

    df = df[df["StockCode"].isin(selected_products)].copy()

    print(f"\nProducts selected for analysis: {len(selected_products)}")

    # Create sparse invoice-product matrix
    print("Creating memory-efficient sparse basket matrix...")

    invoice_codes, invoice_names = pd.factorize(df["Invoice"])
    product_codes, product_names = pd.factorize(df["StockCode"])

    matrix = csr_matrix(
        (
            np.ones(len(df), dtype=bool),
            (invoice_codes, product_codes)
        ),
        shape=(len(invoice_names), len(product_names)),
        dtype=bool
    )

    basket = pd.DataFrame.sparse.from_spmatrix(
        matrix,
        index=invoice_names,
        columns=product_names
    )

    print(f"Basket matrix shape: {basket.shape}")

    # Create product description lookup
    descriptions = (
        df.groupby("StockCode")["Description"]
        .first()
        .fillna("Unknown product")
        .to_dict()
    )

    # Find frequent itemsets using FP-Growth
    print("\nFinding frequent product combinations using FP-Growth...")

    frequent_itemsets = fpgrowth(
        basket,
        min_support=MIN_SUPPORT,
        use_colnames=True,
        max_len=3
    )

    if frequent_itemsets.empty:
        print("No frequent combinations found. Try lowering MIN_SUPPORT.")
        return

    frequent_itemsets["products"] = frequent_itemsets["itemsets"].apply(
        lambda items: readable_items(items, descriptions)
    )

    frequent_itemsets["number_of_products"] = (
        frequent_itemsets["itemsets"].apply(len)
    )

    frequent_itemsets.drop(columns=["itemsets"]).sort_values(
        "support",
        ascending=False
    ).to_csv(
        OUTPUT_DIR / "frequent_itemsets.csv",
        index=False
    )

    # Generate association rules
    print("Generating association rules...")

    rules = association_rules(
        frequent_itemsets,
        metric="confidence",
        min_threshold=MIN_CONFIDENCE
    )

    if rules.empty:
        print("No association rules found. Try lowering MIN_CONFIDENCE.")
        return

    # Keep positive associations
    rules = rules[rules["lift"] > 1].copy()

    if rules.empty:
        print("No rules with lift greater than 1 were found.")
        return

    rules["antecedents"] = rules["antecedents"].apply(
        lambda items: readable_items(items, descriptions)
    )

    rules["consequents"] = rules["consequents"].apply(
        lambda items: readable_items(items, descriptions)
    )

    rules = rules[
        [
            "antecedents",
            "consequents",
            "support",
            "confidence",
            "lift"
        ]
    ].sort_values(
        ["lift", "confidence"],
        ascending=False
    )

    rules.to_csv(
        OUTPUT_DIR / "association_rules.csv",
        index=False
    )

    print("\nTOP 15 PRODUCT ASSOCIATION RULES")
    print("=" * 100)

    print(
        rules.head(15).to_string(
            index=False,
            formatters={
                "support": "{:.3%}".format,
                "confidence": "{:.2%}".format,
                "lift": "{:.2f}".format
            }
        )
    )

    print("\nAnalysis completed successfully!")

    print(f"Frequent itemsets: {OUTPUT_DIR / 'frequent_itemsets.csv'}")
    print(f"Association rules: {OUTPUT_DIR / 'association_rules.csv'}")


if __name__ == "__main__":
    run_market_basket_analysis()

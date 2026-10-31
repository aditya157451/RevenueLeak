
from pathlib import Path

import duckdb
import pandas as pd
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
    KeepTogether,
)


# --------------------------------------------------
# 1. PATHS AND SETTINGS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

PARQUET_PATH = BASE_DIR / "data/processed/online_retail_cleaned.parquet"
RFM_PATH = BASE_DIR / "data/processed/customer_rfm.csv"
RULES_PATH = BASE_DIR / "data/processed/association_rules.csv"

REPORT_DIR = BASE_DIR / "reports"
CHART_DIR = REPORT_DIR / "charts"

REPORT_DIR.mkdir(exist_ok=True)
CHART_DIR.mkdir(exist_ok=True)

PDF_PATH = REPORT_DIR / "RevenueLeak_Business_Analysis_Report.pdf"


# --------------------------------------------------
# 2. LOAD DATA AND CALCULATE BUSINESS METRICS
# --------------------------------------------------

print("Loading analysis data...")

if not PARQUET_PATH.exists():
    raise FileNotFoundError(f"Missing cleaned dataset: {PARQUET_PATH}")

if not RFM_PATH.exists():
    raise FileNotFoundError(f"Missing RFM file: {RFM_PATH}")

if not RULES_PATH.exists():
    raise FileNotFoundError(f"Missing association rules file: {RULES_PATH}")

con = duckdb.connect(database=":memory:")

parquet = str(PARQUET_PATH).replace("\\", "/")

overview = con.execute(f"""
    SELECT
        COUNT(*) AS cleaned_rows,
        SUM(SalesValue) AS total_sales,
        SUM(CancellationValue) AS cancellation_value,
        SUM(NetGrossRevenue) AS net_gross_revenue,
        COUNT(DISTINCT CASE
            WHEN SalesValue > 0 THEN Invoice
        END) AS sales_invoices,
        COUNT(DISTINCT CASE
            WHEN SalesValue > 0 THEN Country
        END) AS countries,
        SUM(CASE
            WHEN "Customer ID" IS NULL THEN NetGrossRevenue
            ELSE 0
        END) AS missing_customer_revenue,
        COUNT(CASE
            WHEN "Customer ID" IS NULL THEN 1
        END) AS missing_customer_rows
    FROM read_parquet('{parquet}')
""").fetchdf().iloc[0]

monthly = con.execute(f"""
    SELECT
        STRFTIME(InvoiceDate, '%Y-%m') AS month,
        SUM(NetGrossRevenue) AS revenue
    FROM read_parquet('{parquet}')
    GROUP BY month
    ORDER BY month
""").fetchdf()

countries = con.execute(f"""
    SELECT
        Country,
        SUM(SalesValue) AS sales,
        SUM(CancellationValue) AS cancellations,
        SUM(NetGrossRevenue) AS net_revenue,
        100.0 * SUM(CancellationValue)
            / NULLIF(SUM(SalesValue), 0) AS cancellation_to_sales_pct
    FROM read_parquet('{parquet}')
    GROUP BY Country
    ORDER BY net_revenue DESC
    LIMIT 10
""").fetchdf()

cancellation_products = con.execute(f"""
    SELECT
        StockCode,
        MAX(Description) AS Description,
        SUM(CancellationValue) AS cancellation_value
    FROM read_parquet('{parquet}')
    WHERE IsCancellation = TRUE
      AND CancellationValue > 0
    GROUP BY StockCode
    ORDER BY cancellation_value DESC
    LIMIT 10
""").fetchdf()

aov = con.execute(f"""
    SELECT AVG(invoice_value) AS average_order_value
    FROM (
        SELECT Invoice, SUM(SalesValue) AS invoice_value
        FROM read_parquet('{parquet}')
        WHERE SalesValue > 0
        GROUP BY Invoice
    )
""").fetchone()[0]

con.close()

rfm = pd.read_csv(RFM_PATH)
rules = pd.read_csv(RULES_PATH)

total_sales = float(overview["total_sales"])
cancellation_value = float(overview["cancellation_value"])
net_revenue = float(overview["net_gross_revenue"])
invoice_count = int(overview["sales_invoices"])
country_count = int(overview["countries"])
cleaned_rows = int(overview["cleaned_rows"])

uk_revenue = float(
    countries.loc[
        countries["Country"] == "United Kingdom", "net_revenue"
    ].iloc[0]
)

uk_share = 100 * uk_revenue / net_revenue if net_revenue else 0

missing_customer_revenue = float(overview["missing_customer_revenue"])
missing_customer_share = (
    100 * missing_customer_revenue / net_revenue if net_revenue else 0
)

at_risk_count = int(
    rfm["segment"].isin(["At Risk", "Hibernating"]).sum()
)

rfm_count = len(rfm)
at_risk_share = 100 * at_risk_count / rfm_count if rfm_count else 0

# Market basket: show the strongest rule by lift.
best_rule = rules.sort_values("lift", ascending=False).iloc[0] if not rules.empty else None


# --------------------------------------------------
# 3. CREATE CHARTS
# --------------------------------------------------

print("Generating charts...")


def save_chart(path):
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


# Monthly revenue
plt.figure(figsize=(9, 3.5))
plt.plot(
    monthly["month"],
    monthly["revenue"],
    marker="o"
)
plt.title("Monthly Net Gross Revenue")
plt.xlabel("Month")
plt.ylabel("Revenue (original currency units)")
plt.xticks(rotation=60, ha="right")
save_chart(CHART_DIR / "monthly_revenue.png")


# Top countries
plt.figure(figsize=(8, 4))
country_chart = countries.head(8).sort_values("net_revenue")
plt.barh(country_chart["Country"], country_chart["net_revenue"])
plt.title("Top Countries by Net Gross Revenue")
plt.xlabel("Revenue (original currency units)")
save_chart(CHART_DIR / "country_revenue.png")


# RFM segments
segment_counts = rfm["segment"].value_counts()

plt.figure(figsize=(7, 4))
plt.bar(segment_counts.index, segment_counts.values)
plt.title("Customer Segments (RFM)")
plt.xlabel("Segment")
plt.ylabel("Number of customers")
plt.xticks(rotation=35, ha="right")
save_chart(CHART_DIR / "rfm_segments.png")


# Cancellation products
plt.figure(figsize=(8, 4))
cancel_chart = cancellation_products.head(8).sort_values(
    "cancellation_value"
)
labels = (
    cancel_chart["StockCode"].astype(str)
    + " - "
    + cancel_chart["Description"].astype(str).str.slice(0, 30)
)
plt.barh(labels, cancel_chart["cancellation_value"])
plt.title("Products with Highest Cancellation Value")
plt.xlabel("Cancellation value (original currency units)")
save_chart(CHART_DIR / "cancellation_products.png")


# --------------------------------------------------
# 4. REPORT STYLES
# --------------------------------------------------

styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    name="ReportTitle",
    parent=styles["Title"],
    fontSize=25,
    leading=31,
    alignment=TA_CENTER,
    textColor=colors.HexColor("#17365D"),
    spaceAfter=15,
))

styles.add(ParagraphStyle(
    name="SectionTitle",
    parent=styles["Heading1"],
    fontSize=17,
    leading=21,
    textColor=colors.HexColor("#17365D"),
    spaceBefore=8,
    spaceAfter=10,
))

styles.add(ParagraphStyle(
    name="SubTitle",
    parent=styles["Heading2"],
    fontSize=11,
    leading=14,
    textColor=colors.HexColor("#2874A6"),
    spaceBefore=7,
    spaceAfter=5,
))

styles.add(ParagraphStyle(
    name="BodyCustom",
    parent=styles["BodyText"],
    fontSize=9,
    leading=13,
    spaceAfter=7,
))

styles.add(ParagraphStyle(
    name="SmallCustom",
    parent=styles["BodyText"],
    fontSize=7.5,
    leading=10,
    spaceAfter=4,
))

styles.add(ParagraphStyle(
    name="CoverSubtitle",
    parent=styles["BodyText"],
    fontSize=12,
    leading=18,
    alignment=TA_CENTER,
    textColor=colors.HexColor("#555555"),
))


# --------------------------------------------------
# 5. HELPER FUNCTIONS
# --------------------------------------------------

story = []


def add_paragraph(text, style="BodyCustom"):
    story.append(Paragraph(str(text), styles[style]))


def add_heading(text):
    story.append(Paragraph(text, styles["SectionTitle"]))


def add_table(data, widths=None):
    table = Table(data, colWidths=widths, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#F2F5F8")
        ]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    story.append(table)
    story.append(Spacer(1, 9))


def add_chart(filename, width=6.5 * inch):
    path = CHART_DIR / filename
    story.append(Image(str(path), width=width, height=width * 0.43))
    story.append(Spacer(1, 7))


def money(value):
    return f"{value:,.2f}"


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)

    canvas.drawString(
        0.65 * inch,
        0.4 * inch,
        "RevenueLeak | Business Analysis Report"
    )

    canvas.drawRightString(
        7.85 * inch,
        0.4 * inch,
        f"Page {doc.page}"
    )

    canvas.restoreState()


# --------------------------------------------------
# 6. PAGE 1 - COVER AND EXECUTIVE SUMMARY
# --------------------------------------------------

story.append(Spacer(1, 0.8 * inch))
add_paragraph("REVENUELEAK", "ReportTitle")
add_paragraph(
    "Revenue, Customer and Product Performance Analysis",
    "CoverSubtitle"
)

story.append(Spacer(1, 0.3 * inch))

add_paragraph(
    "Business Analysis Report",
    "CoverSubtitle"
)

story.append(Spacer(1, 0.5 * inch))

add_heading("Executive Summary")

add_paragraph(
    "This report analyzes the Online Retail II transaction dataset to identify "
    "revenue patterns, cancellation exposure, customer engagement opportunities "
    "and product combinations that may support cross-selling."
)

add_paragraph(
    f"The cleaned dataset contains <b>{cleaned_rows:,}</b> transaction-line "
    f"records across <b>{country_count}</b> countries. The analysis identifies "
    f"<b>{money(total_sales)}</b> in sales value and "
    f"<b>{money(cancellation_value)}</b> in identified cancellation value, "
    f"resulting in preliminary Net Gross Revenue of "
    f"<b>{money(net_revenue)}</b>."
)

kpi_data = [
    ["Business metric", "Result"],
    ["Total sales value", money(total_sales)],
    ["Cancellation value", money(cancellation_value)],
    ["Preliminary Net Gross Revenue", money(net_revenue)],
    ["Sales invoices", f"{invoice_count:,}"],
    ["Average Order Value", money(aov)],
    ["Customers in RFM analysis", f"{rfm_count:,}"],
]

add_table(kpi_data, [3.2 * inch, 3.0 * inch])

add_heading("Headline Findings")

add_paragraph(
    f"<b>Market concentration:</b> The United Kingdom contributes "
    f"{uk_share:.1f}% of preliminary Net Gross Revenue."
)

add_paragraph(
    f"<b>Customer engagement:</b> {at_risk_count:,} customers "
    f"({at_risk_share:.1f}%) are classified as At Risk or Hibernating "
    f"under the rule-based RFM segmentation."
)

if best_rule is not None:
    add_paragraph(
        f"<b>Product association:</b> The strongest discovered rule by lift "
        f"has a lift of {float(best_rule['lift']):.2f} and confidence of "
        f"{float(best_rule['confidence']):.1%}."
    )

add_paragraph(
    "<b>Purpose:</b> Provide practical, evidence-based actions for revenue "
    "monitoring, customer retention and product recommendations."
)

story.append(PageBreak())


# --------------------------------------------------
# 7. PAGE 2 - DATA AND METHODOLOGY
# --------------------------------------------------

add_heading("1. Dataset and Methodology")

add_paragraph(
    "The analysis uses the Online Retail II dataset, which contains retail "
    "transaction records from December 2009 to December 2011. Each row "
    "represents a product line within an invoice."
)

add_paragraph("<b>Data preparation approach</b>", "SubTitle")

method_data = [
    ["Area", "Treatment"],
    ["Duplicate records", "Exact duplicate rows removed."],
    ["Invoice dates", "Parsed into date-time values; invalid dates excluded."],
    ["Price", "Rows with zero or negative prices excluded."],
    ["Cancellations", "Invoices beginning with C handled separately."],
    ["Missing Customer IDs", "Retained in revenue totals; excluded from RFM."],
    ["Negative quantities", "Non-cancellation negative adjustments with non-positive prices excluded."],
    ["Storage", "Cleaned records stored in Parquet and queried using DuckDB."],
]

add_table(method_data, [1.7 * inch, 4.5 * inch])

add_paragraph("<b>Revenue definitions</b>", "SubTitle")

add_paragraph(
    "Sales Value is calculated from eligible positive-quantity sales lines. "
    "Cancellation Value is the absolute value of identified cancellation "
    "invoice lines. Preliminary Net Gross Revenue is calculated as Sales "
    "Value minus Cancellation Value."
)

add_paragraph(
    "<b>Important:</b> This dataset does not provide product cost or operating "
    "expense data. Therefore, the report does not calculate profit or profit "
    "margin. The term Net Gross Revenue is used only for sales less identified "
    "cancellation value."
)

add_paragraph(
    f"The cleaned dataset contains {cleaned_rows:,} rows. Revenue from "
    f"transactions with missing Customer IDs is {money(missing_customer_revenue)}, "
    f"approximately {missing_customer_share:.1f}% of preliminary Net Gross Revenue. "
    "These transactions remain included in overall revenue calculations."
)

add_paragraph("<b>Analytical methods</b>", "SubTitle")

add_paragraph(
    "Revenue trends are calculated monthly and by country. Average Order Value "
    "is the average of invoice-level positive sales values. Customer analysis "
    "uses Recency, Frequency and Monetary (RFM) measures. Market Basket Analysis "
    "uses FP-Growth to identify frequently co-purchased products and association "
    "rules."
)

add_paragraph(
    "For market basket analysis, the 500 most frequently purchased products "
    "were selected, with a minimum occurrence threshold of 20 invoices. "
    "The analysis included 37,083 invoices containing at least one selected "
    "product. Minimum support was 1%, minimum confidence was 20%, and only "
    "rules with lift greater than 1 were retained."
)

story.append(PageBreak())


# --------------------------------------------------
# 8. PAGE 3 - REVENUE AND COUNTRY PERFORMANCE
# --------------------------------------------------

add_heading("2. Revenue Performance")

add_paragraph(
    "The monthly revenue trend provides a view of changes in transaction "
    "performance over the dataset period. Peaks and declines can help "
    "management identify periods for further operational investigation."
)

add_chart("monthly_revenue.png")

add_paragraph("<b>Country contribution</b>", "SubTitle")

country_table = [["Country", "Sales", "Cancellation value", "Net gross revenue"]]

for _, row in countries.head(8).iterrows():
    country_table.append([
        str(row["Country"]),
        money(row["sales"]),
        money(row["cancellations"]),
        money(row["net_revenue"]),
    ])

add_table(
    country_table,
    [1.35 * inch, 1.55 * inch, 1.55 * inch, 1.75 * inch]
)

add_chart("country_revenue.png")

add_paragraph(
    f"The United Kingdom is the largest market, contributing "
    f"{uk_share:.1f}% of preliminary Net Gross Revenue "
    f"({money(uk_revenue)}). This concentration makes UK performance "
    "particularly important to overall revenue monitoring."
)

add_paragraph(
    f"Average Order Value across {invoice_count:,} eligible sales invoices "
    f"is {money(aov)}. AOV is an invoice-level average of positive sales "
    "value and does not represent profit."
)

story.append(PageBreak())


# --------------------------------------------------
# 9. PAGE 4 - CUSTOMER AND CANCELLATION ANALYSIS
# --------------------------------------------------

add_heading("3. Customer and Cancellation Analysis")

add_paragraph(
    "RFM analysis groups customers according to how recently they purchased, "
    "how frequently they purchased and how much positive sales value they "
    "generated. The segments are rule-based classifications, not predictive "
    "models."
)

add_chart("rfm_segments.png")

segment_table = [["RFM segment", "Customers"]]

for segment, count in segment_counts.items():
    segment_table.append([str(segment), f"{int(count):,}"])

add_table(segment_table, [3.5 * inch, 2.7 * inch])

add_paragraph(
    f"There are {at_risk_count:,} At Risk and Hibernating customers, "
    f"representing {at_risk_share:.1f}% of the analyzed customer base. "
    "This group is a potential audience for carefully tested re-engagement "
    "campaigns."
)

add_paragraph("<b>Cancellation exposure by product</b>", "SubTitle")

add_chart("cancellation_products.png")

cancel_table = [["Product", "Cancellation value"]]

for _, row in cancellation_products.head(5).iterrows():
    name = str(row["Description"])[:42]
    cancel_table.append([
        name,
        money(row["cancellation_value"])
    ])

add_table(cancel_table, [4.4 * inch, 1.8 * inch])

add_paragraph(
    "The products shown are ranked by cancellation value in cancellation "
    "invoices. These records do not necessarily identify the original sale "
    "invoice or explain why a cancellation occurred. The results should be "
    "used to prioritize investigation rather than infer product defects."
)

story.append(PageBreak())


# --------------------------------------------------
# 10. PAGE 5 - MARKET BASKET AND RECOMMENDATIONS
# --------------------------------------------------

add_heading("4. Product Association Analysis")

add_paragraph(
    "Market Basket Analysis identifies products that frequently appear "
    "together in the same invoice. Support measures how common a combination "
    "is, confidence measures how often the consequent product appears when "
    "the antecedent is present, and lift compares that likelihood with the "
    "consequent product's overall frequency."
)

if not rules.empty:
    rule_table = [["Products purchased together", "Confidence", "Lift"]]

    for _, row in rules.head(6).iterrows():
        antecedent = str(row["antecedents"])[:75]
        consequent = str(row["consequents"])[:55]

        rule_table.append([
            Paragraph(
                f"{antecedent}<br/><b>Also:</b> {consequent}",
                styles["SmallCustom"]
            ),
            f"{float(row['confidence']):.1%}",
            f"{float(row['lift']):.2f}",
        ])

    add_table(
        rule_table,
        [4.4 * inch, 0.9 * inch, 0.9 * inch]
    )

    add_paragraph(
        "The strongest associations include the Poppy's Playhouse Bedroom, "
        "Kitchen and Livingroom products, as well as matching mug and cup "
        "collections. These combinations may be useful for testing product "
        "bundles and recommendation placements."
    )

add_heading("5. Prioritized Business Recommendations")

add_paragraph(
    "<b>1. Improve customer retention.</b> Start with At Risk and Hibernating "
    "customers. Test targeted reminders, relevant product suggestions and "
    "limited promotions. Track repeat purchase rate and revenue generated "
    "by each campaign."
)

add_paragraph(
    "<b>2. Test cross-selling and product bundles.</b> Use the strongest "
    "product associations to create bundle suggestions or complementary "
    "product placements. Measure conversion, order value and incremental "
    "revenue before scaling."
)

add_paragraph(
    "<b>3. Investigate cancellations and customer identification.</b> "
    "Prioritize the UK because it has the largest absolute cancellation "
    "value. Review cancellation records and operational processes. Improve "
    "Customer ID capture to strengthen customer-level reporting."
)

add_heading("6. Limitations and Next Steps")

add_paragraph(
    "The analysis is descriptive and does not establish causal relationships. "
    "Cancellation invoices may not be directly matched to original sales "
    "invoices. Cancellation-to-sales value ratios are not the percentage of "
    "invoices cancelled or a confirmed customer return rate."
)

add_paragraph(
    "RFM Monetary values are based on positive Sales Value, rather than "
    "customer-level cancellation-adjusted revenue. Market basket results "
    "are limited to the selected 500 products and the invoices containing "
    "at least one of those products. Association does not imply causation."
)

add_paragraph(
    "Recommended next steps include validating cancellation reasons, "
    "testing retention campaigns, evaluating bundle performance and "
    "improving customer identification in transaction records."
)

add_paragraph(
    "<b>Conclusion:</b> RevenueLeak provides a consolidated view of revenue, "
    "customer engagement, cancellation exposure and product associations. "
    "The findings provide a practical starting point for focused business "
    "experiments and ongoing performance monitoring."
)


# --------------------------------------------------
# 11. GENERATE PDF
# --------------------------------------------------

print("\nGenerating business report...")

document = SimpleDocTemplate(
    str(PDF_PATH),
    pagesize=A4,
    rightMargin=0.65 * inch,
    leftMargin=0.65 * inch,
    topMargin=0.6 * inch,
    bottomMargin=0.65 * inch,
)

document.build(
    story,
    onFirstPage=footer,
    onLaterPages=footer
)

print("\nREPORT GENERATED SUCCESSFULLY!")
print(f"PDF location: {PDF_PATH}")
print(f"Report size: {PDF_PATH.stat().st_size / 1024:.2f} KB")

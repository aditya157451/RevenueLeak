# RevenueLeak — Retail Revenue Intelligence & Cancellation Analysis

**An end-to-end retail analytics platform built using Python, FastAPI, Streamlit, DuckDB and Plotly.**

RevenueLeak analyzes the [Online Retail II dataset](https://archive.ics.uci.edu/dataset/502/online+retail+ii) to help businesses understand revenue performance, identify cancellation patterns, analyze customer behavior and discover product associations.

The project transforms raw retail transaction data into actionable business insights through a data processing pipeline, REST APIs and an interactive analytics dashboard.

---

## Project Overview

Online retailers generate large volumes of transaction data, but identifying revenue patterns, customer behavior and cancellation trends can be challenging.

RevenueLeak addresses this problem through an automated analytics workflow that:

- Cleans and validates raw retail transaction data.
- Calculates sales, cancellation values and net gross revenue.
- Analyzes monthly and country-wise revenue performance.
- Identifies high-performing and frequently cancelled products.
- Segments customers using RFM analysis.
- Discovers product associations using Market Basket Analysis.
- Provides business insights through an interactive dashboard and REST APIs.

## Technology Stack

| Component | Technologies |
|---|---|
| Programming Language | Python |
| Data Processing | Pandas, NumPy |
| Database / Query Engine | DuckDB |
| Data Storage | Parquet, CSV |
| Backend | FastAPI |
| API Testing | Swagger UI, Pytest, HTTPX |
| Frontend | Streamlit |
| Data Visualization | Plotly, Matplotlib |
| Customer Segmentation | RFM Analysis |
| Market Basket Analysis | MLxtend, FP-Growth |
| Report Generation | ReportLab |

## System Architecture

```text
                 Online Retail II Dataset
                           |
                           v
                   Data Cleaning
                     (Pandas)
                           |
                           v
                Processed Parquet Data
                           |
                           v
                      DuckDB
                           |
              +------------+------------+
              |                         |
              v                         v
         FastAPI Backend          Analytics Scripts
              |                         |
              v                  +------+------+
         REST Endpoints           |             |
              |                   v             v
              |              RFM Analysis   FP-Growth
              |                   |             |
              |                   v             v
              |              Customer      Association
              |              Segments         Rules
              |                   |             |
              +-------------------+-------------+
                                  |
                                  v
                         Streamlit Dashboard
                                  |
                                  v
                       Business Insights & Reports
```

## Dataset

**Source:** [UCI Machine Learning Repository — Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii)

The dataset contains transactions from a UK-based online retailer.

| Attribute | Details |
|---|---|
| Original records | 1,067,371 |
| Time period | December 2009 – December 2011 |
| Original columns | 8 |
| Countries | 43 |
| Unique customers in cleaned analysis | 5,878 |

Important dataset columns:

- `Invoice`: Invoice number.
- `StockCode`: Product identifier.
- `Description`: Product description.
- `Quantity`: Number of products purchased.
- `InvoiceDate`: Transaction date and time.
- `Price`: Unit price.
- `Customer ID`: Customer identifier.
- `Country`: Customer's country.

## Data Cleaning & Processing

The raw dataset is processed using Pandas.

Key cleaning operations:

1. Load the original dataset using the appropriate file encoding.
2. Standardize column names and text values.
3. Parse invoice dates.
4. Convert customer identifiers into a consistent numeric format.
5. Remove exact duplicate records.
6. Identify cancellation invoices using invoice numbers beginning with `C`.
7. Exclude records with non-positive prices.
8. Investigate and exclude non-cancellation negative-quantity adjustment records with non-positive prices.
9. Preserve transactions with missing Customer IDs for overall revenue analysis.

### Revenue Calculation

The project distinguishes between normal sales and identified cancellation values.

**Sales Value**

`Quantity × Price` for eligible positive-quantity sales.

**Cancellation Value**

Absolute transaction value for identified cancellation invoices with negative quantities.

**Net Gross Revenue**

`Sales Value − Cancellation Value`

Net Gross Revenue is an analytical measure, not profit. The dataset does not contain product cost information.

Missing Customer IDs are included in overall revenue calculations but excluded from customer-level RFM analysis.

## Key Business Findings

The following findings were calculated from the processed dataset.

### 1. Revenue Performance

- Total Sales Value: approximately 20.48 million.
- Identified Cancellation Value: approximately 1.46 million.
- Preliminary Net Gross Revenue: approximately 19.01 million.

### 2. Geographic Revenue Distribution

- The United Kingdom contributes approximately 84.9% of preliminary Net Gross Revenue.
- The UK also accounts for the largest absolute cancellation value.

### 3. Customer Segmentation

RFM analysis identified 5,878 customers.

- 1,299 Champions.
- 707 Loyal Customers.
- 820 At Risk customers.
- 1,531 Hibernating customers.

Approximately 40% of identified customers fall into the At Risk or Hibernating segments.

### 4. Product Associations

FP-Growth identified frequently purchased product combinations.

For example, purchasing Poppy's Playhouse Bedroom and Kitchen products was associated with purchasing the Livingroom product, with approximately 73.43% confidence and a lift of 48.28 in the analyzed baskets.

### 5. Customer Data Quality

Approximately 2.72 million in sales value is associated with transactions missing Customer IDs. This limits customer-level analysis coverage.

## Business Recommendations

1. **Customer Retention:** Design targeted re-engagement campaigns for At Risk and Hibernating customer segments.
2. **Product Bundling:** Test product bundles and recommendations using frequently associated products.
3. **Cancellation Monitoring:** Investigate cancellation patterns, particularly in markets with high absolute cancellation values.
4. **Customer Identification:** Improve Customer ID capture to strengthen customer analytics.

These are recommendations based on observed associations and transaction patterns, not proven causal effects.

## Project Structure

```text
Revenue_Leak_project/
│
├── api/
│   ├── __init__.py
│   └── main.py
│
├── dashboard/
│   └── app.py
│
├── data/
│   ├── raw/
│   │   └── online_retail_II.csv
│   │
│   └── processed/
│       ├── online_retail_cleaned.parquet
│       ├── customer_rfm.csv
│       ├── frequent_itemsets.csv
│       └── association_rules.csv
│
├── reports/
│   ├── charts/
│   └── RevenueLeak_Business_Analysis_Report.pdf
│
├── scripts/
│   ├── clean_data.py
│   ├── explore_data.py
│   ├── verify_parquet.py
│   ├── investigate_negative_rows.py
│   ├── explore_duckdb.py
│   ├── analyze_rfm.py
│   ├── market_basket_analysis.py
│   └── generate_business_report.py
│
├── src/
│   ├── __init__.py
│   └── cleaning.py
│
├── tests/
│   ├── __init__.py
│   ├── test_cleaning.py
│   └── test_api.py
│
├── requirements.txt
├── .gitignore
└── README.md
```

## Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/RevenueLeak.git
cd RevenueLeak
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Download the dataset

Download Online Retail II from the UCI Machine Learning Repository.

Place the dataset in:

```text
data/raw/online_retail_II.csv
```

Use the appropriate CSV export and filename expected by the cleaning script.

### 5. Run the data processing pipeline

```bash
python scripts/clean_data.py
```

### 6. Generate customer segmentation

```bash
python scripts/analyze_rfm.py
```

### 7. Generate Market Basket Analysis

```bash
python scripts/market_basket_analysis.py
```

### 8. Start the FastAPI backend

```bash
uvicorn api.main:app --reload
```

Backend URL:

`http://127.0.0.1:8000`

Swagger API documentation:

`http://127.0.0.1:8000/docs`

### 9. Start the Streamlit dashboard

Open a second terminal and run:

```bash
streamlit run dashboard/app.py
```

Dashboard URL:

`http://localhost:8501`

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | API welcome message |
| GET | `/health` | Backend health check |
| GET | `/api/overview` | Revenue overview |
| GET | `/api/monthly-revenue` | Monthly revenue trends |
| GET | `/api/countries` | Available countries |
| GET | `/api/products/top` | Top-selling products |
| GET | `/api/products/cancellations` | Products with high cancellation values |
| GET | `/api/customers/segments` | Customer segment summary |
| GET | `/api/customers/top` | Top customers by monetary value |

Optional filters are available on supported endpoints. Explore `/docs` for parameters and response schemas.

## Testing

Run the automated tests using:

```bash
python -m pytest tests/ -v
```

The API test suite currently includes 10 passing tests.

## Business Report

A PDF business analysis report is generated using ReportLab.

Expected location:

```text
reports/RevenueLeak_Business_Analysis_Report.pdf
```

The report covers:

- Executive summary.
- Data cleaning methodology.
- Revenue and geographic analysis.
- RFM customer segmentation.
- Product cancellation analysis.
- Market Basket findings.
- Business recommendations and limitations.

## Limitations

- The dataset does not provide product costs, so profit cannot be calculated.
- Missing Customer IDs limit customer-level analysis.
- Cancellation values are identified from cancellation invoices and may not be directly matched to original sales invoices.
- RFM segments are descriptive, rule-based segments rather than predictive models.
- Market Basket associations indicate co-purchasing patterns, not causation.
- Market Basket support is calculated over invoices containing at least one of the selected products used in the analysis.

## Future Improvements

- Add date-range and comparative-period filters.
- Integrate the Streamlit dashboard directly with FastAPI endpoints.
- Add automated data quality monitoring.
- Implement customer retention and churn prediction.
- Deploy the application using Docker and a cloud platform.

## Author

**Aditya Kumar**

B.Tech — Computer Science & Engineering

Interested in Python Backend Development, Data Analytics and AI/ML.

---

*RevenueLeak — Turning retail transaction data into actionable business insights.*
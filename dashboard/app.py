
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# --------------------------------------------------
# 1. PROJECT CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

PARQUET_PATH = (
    BASE_DIR / "data" / "processed" / "online_retail_cleaned.parquet"
)

RFM_PATH = (
    BASE_DIR / "data" / "processed" / "customer_rfm.csv"
)

BASKET_PATH = (
    BASE_DIR / "data" / "processed" / "association_rules.csv"
)

st.set_page_config(
    page_title="RevenueLeak | Retail Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Brand colors
PRIMARY = "#2563EB"
DARK = "#14213D"
GREEN = "#16A085"
ORANGE = "#E67E22"
RED = "#E74C3C"
MUTED = "#64748B"


# --------------------------------------------------
# 2. CUSTOM CSS
# --------------------------------------------------

st.markdown("""
<style>

/* Main application */
.stApp {
    background-color: #F5F7FB;
}

/* Main content spacing */
.block-container {
    padding-top: 1.8rem;
    padding-bottom: 2rem;
    max-width: 1500px;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #14213D;
}

[data-testid="stSidebar"] * {
    color: #FFFFFF;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label {
    padding: 7px 10px;
    border-radius: 8px;
}

/* Sidebar divider */
[data-testid="stSidebar"] hr {
    border-color: #34445F;
}

/* KPI cards */
[data-testid="stMetric"] {
    background-color: #FFFFFF;
    border: 1px solid #E5EAF2;
    padding: 18px;
    border-radius: 14px;
    box-shadow: 0 3px 12px rgba(20, 33, 61, 0.04);
}

[data-testid="stMetricLabel"] {
    color: #64748B;
    font-size: 14px;
}

[data-testid="stMetricValue"] {
    color: #14213D;
    font-weight: 700;
}

/* Headings */
h1, h2, h3 {
    color: #14213D;
}

/* Chart containers */
[data-testid="stPlotlyChart"] {
    background-color: #FFFFFF;
    border: 1px solid #E5EAF2;
    border-radius: 14px;
    padding: 8px;
}

/* Dataframes */
[data-testid="stDataFrame"] {
    border: 1px solid #E5EAF2;
    border-radius: 12px;
}

/* Buttons and select boxes */
.stSelectbox > div > div {
    border-radius: 8px;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }

    [data-testid="stMetric"] {
        padding: 12px;
    }
}

</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# 3. DATA VALIDATION
# --------------------------------------------------

if not PARQUET_PATH.exists():
    st.error("Cleaned dataset not found. Run scripts/clean_data.py first.")
    st.stop()

if not RFM_PATH.exists():
    st.error("RFM data not found. Run scripts/analyze_rfm.py first.")
    st.stop()


# --------------------------------------------------
# 4. DATA FUNCTIONS
# --------------------------------------------------

@st.cache_data
def get_countries():
    con = duckdb.connect(database=":memory:")

    result = con.execute(
        """
        SELECT DISTINCT Country
        FROM read_parquet(?)
        WHERE Country IS NOT NULL
        ORDER BY Country
        """,
        [str(PARQUET_PATH)]
    ).fetchdf()

    con.close()

    return result["Country"].tolist()


@st.cache_data
def get_data(country):

    con = duckdb.connect(database=":memory:")

    source = f"read_parquet('{PARQUET_PATH.as_posix()}')"

    where_clause = (
        "" if country == "All"
        else "WHERE Country = ?"
    )

    params = [] if country == "All" else [country]

    def query(sql):
        return con.execute(sql, params).fetchdf()

    # Revenue overview
    kpis = query(f"""
        SELECT
            SUM(SalesValue) AS sales,
            SUM(CancellationValue) AS cancellations,
            SUM(NetGrossRevenue) AS net_revenue,

            COUNT(DISTINCT Invoice) FILTER (
                WHERE IsCancellation = FALSE
                AND SalesValue > 0
            ) AS invoices

        FROM {source}
        {where_clause}
    """)

    # Monthly revenue
    monthly = query(f"""
        SELECT
            STRFTIME(InvoiceDate, '%Y-%m') AS month,
            SUM(SalesValue) AS sales,
            SUM(CancellationValue) AS cancellations,
            SUM(NetGrossRevenue) AS net_revenue

        FROM {source}
        {where_clause}

        GROUP BY month
        ORDER BY month
    """)

    # Country revenue
    countries = query(f"""
        SELECT
            Country,
            SUM(NetGrossRevenue) AS revenue

        FROM {source}
        {where_clause}

        GROUP BY Country
        ORDER BY revenue DESC
        LIMIT 10
    """)

    # Cancellation ratio
    cancellation = query(f"""
        SELECT
            Country,
            SUM(SalesValue) AS sales,
            SUM(CancellationValue) AS cancellations,

            ROUND(
                100.0 * SUM(CancellationValue)
                / NULLIF(SUM(SalesValue), 0),
                2
            ) AS cancellation_ratio

        FROM {source}
        {where_clause}

        GROUP BY Country

        HAVING SUM(SalesValue) > 0

        ORDER BY cancellation_ratio DESC
        LIMIT 10
    """)

    # Best-selling products
    products = query(f"""
        SELECT
            Description,
            SUM(SalesValue) AS sales

        FROM {source}
        {where_clause}

        GROUP BY Description
        ORDER BY sales DESC
        LIMIT 10
    """)

    # Products with cancellation value
    returned_products = query(f"""
        SELECT
            Description,
            SUM(CancellationValue) AS cancellation_value

        FROM {source}
        {where_clause}

        GROUP BY Description

        HAVING SUM(CancellationValue) > 0

        ORDER BY cancellation_value DESC
        LIMIT 10
    """)

    con.close()

    return (
        kpis,
        monthly,
        countries,
        cancellation,
        products,
        returned_products
    )


@st.cache_data
def get_rfm_data():
    return pd.read_csv(RFM_PATH)


@st.cache_data
def get_basket_data():
    if BASKET_PATH.exists():
        return pd.read_csv(BASKET_PATH)

    return pd.DataFrame()


# --------------------------------------------------
# 5. CHART CONFIGURATION
# --------------------------------------------------

def style_chart(fig, height=400):

    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=15, r=15, t=55, b=20),
        font=dict(
            family="Arial",
            size=12,
            color=DARK
        ),
        title_font=dict(
            size=16,
            color=DARK
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=12
        )
    )

    fig.update_xaxes(showgrid=True, gridcolor="#EDF1F7")
    fig.update_yaxes(showgrid=False)

    return fig


# --------------------------------------------------
# 6. LOAD DATA
# --------------------------------------------------

rfm = get_rfm_data()

(
    kpis,
    monthly,
    countries,
    cancellation,
    products,
    returned_products
) = get_data("All")

basket = get_basket_data()


# --------------------------------------------------
# 7. SIDEBAR NAVIGATION
# --------------------------------------------------

with st.sidebar:

    st.markdown(
        """
        <div style="padding: 12px 0 20px 0;">
            <h1 style="color:white; margin-bottom:0;">
                📊 RevenueLeak
            </h1>
            <p style="color:#AAB8CE; font-size:13px;">
                Retail Intelligence Platform
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.markdown("### NAVIGATION")

    page = st.radio(
        "Navigate",
        [
            "Overview",
            "Revenue Analytics",
            "Country Analysis",
            "Product Analysis",
            "Customer Insights",
            "Market Basket"
        ],
        label_visibility="collapsed"
    )

    st.divider()

    st.markdown("### FILTERS")

    country_options = ["All"] + get_countries()

    selected_country = st.selectbox(
        "Select Country",
        country_options
    )

    st.divider()

    st.markdown(
        """
        <div style="color:#AAB8CE; font-size:12px;">
            <b>DATA SOURCE</b><br>
            Online Retail II<br><br>
            <b>PERIOD</b><br>
            December 2009 – December 2011
        </div>
        """,
        unsafe_allow_html=True
    )


# Load selected country data
(
    kpis,
    monthly,
    countries,
    cancellation,
    products,
    returned_products
) = get_data(selected_country)

sales = float(kpis.iloc[0]["sales"] or 0)
cancelled = float(kpis.iloc[0]["cancellations"] or 0)
net_revenue = float(kpis.iloc[0]["net_revenue"] or 0)
invoice_count = int(kpis.iloc[0]["invoices"] or 0)


# --------------------------------------------------
# 8. REUSABLE KPI SECTION
# --------------------------------------------------

def show_kpis():

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Sales",
        f"£{sales:,.2f}"
    )

    c2.metric(
        "Cancellation Value",
        f"£{cancelled:,.2f}"
    )

    c3.metric(
        "Net Gross Revenue",
        f"£{net_revenue:,.2f}"
    )

    c4.metric(
        "Sales Invoices",
        f"{invoice_count:,}"
    )

    st.caption(
        "Net Gross Revenue = Sales Value − identified Cancellation Value. "
        "This is not profit. Currency is GBP."
    )


# --------------------------------------------------
# 9. OVERVIEW PAGE
# --------------------------------------------------

if page == "Overview":

    st.title("Business Overview")

    st.markdown(
        "### Understand your retail business performance"
    )

    st.caption(
        "A high-level view of sales, cancellations and customer activity."
    )

    show_kpis()

    st.divider()

    left, right = st.columns([2, 1])

    with left:

        st.subheader("Revenue Performance")

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=monthly["month"],
            y=monthly["sales"],
            mode="lines+markers",
            name="Sales",
            line=dict(color=PRIMARY, width=3)
        ))

        fig.add_trace(go.Scatter(
            x=monthly["month"],
            y=monthly["net_revenue"],
            mode="lines+markers",
            name="Net Gross Revenue",
            line=dict(color=GREEN, width=3)
        ))

        fig = style_chart(fig, 380)

        st.plotly_chart(fig, width="stretch")

    with right:

        st.subheader("Revenue Breakdown")

        breakdown = pd.DataFrame({
            "Category": ["Sales", "Cancellations"],
            "Value": [sales, cancelled]
        })

        fig = px.pie(
            breakdown,
            names="Category",
            values="Value",
            hole=0.65,
            color="Category",
            color_discrete_map={
                "Sales": PRIMARY,
                "Cancellations": ORANGE
            }
        )

        fig = style_chart(fig, 380)

        st.plotly_chart(fig, width="stretch")

    st.divider()

    left, right = st.columns(2)

    with left:

        st.subheader("Top Performing Countries")

        fig = px.bar(
            countries.sort_values("revenue"),
            x="revenue",
            y="Country",
            orientation="h",
            color_discrete_sequence=[PRIMARY],
            labels={
                "revenue": "Revenue (£)",
                "Country": ""
            }
        )

        fig = style_chart(fig, 350)

        st.plotly_chart(fig, width="stretch")

    with right:

        st.subheader("Customer Segments")

        segment_counts = (
            rfm["segment"]
            .value_counts()
            .rename_axis("segment")
            .reset_index(name="customers")
        )

        fig = px.pie(
            segment_counts,
            names="segment",
            values="customers",
            hole=0.55,
            color_discrete_sequence=px.colors.qualitative.Set2
        )

        fig = style_chart(fig, 350)

        st.plotly_chart(fig, width="stretch")


# --------------------------------------------------
# 10. REVENUE ANALYTICS PAGE
# --------------------------------------------------

elif page == "Revenue Analytics":

    st.title("Revenue Analytics")

    st.caption(
        "Explore monthly sales, cancellation values and net gross revenue."
    )

    show_kpis()

    st.divider()

    st.subheader("Monthly Revenue Trend")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=monthly["month"],
        y=monthly["sales"],
        mode="lines+markers",
        name="Sales",
        line=dict(color=PRIMARY, width=3)
    ))

    fig.add_trace(go.Scatter(
        x=monthly["month"],
        y=monthly["cancellations"],
        mode="lines+markers",
        name="Cancellations",
        line=dict(color=RED, width=2)
    ))

    fig.add_trace(go.Scatter(
        x=monthly["month"],
        y=monthly["net_revenue"],
        mode="lines+markers",
        name="Net Gross Revenue",
        line=dict(color=GREEN, width=3)
    ))

    fig = style_chart(fig, 470)

    st.plotly_chart(fig, width="stretch")

    st.subheader("Monthly Revenue Data")

    monthly_display = monthly.copy()

    for column in ["sales", "cancellations", "net_revenue"]:
        monthly_display[column] = monthly_display[column].round(2)

    st.dataframe(
        monthly_display,
        width="stretch",
        hide_index=True
    )


# --------------------------------------------------
# 11. COUNTRY ANALYSIS PAGE
# --------------------------------------------------

elif page == "Country Analysis":

    st.title("Country Performance")

    st.caption(
        "Understand geographic revenue distribution and cancellation value."
    )

    left, right = st.columns(2)

    with left:

        st.subheader("Top Countries by Revenue")

        fig = px.bar(
            countries.sort_values("revenue"),
            x="revenue",
            y="Country",
            orientation="h",
            color_discrete_sequence=[PRIMARY],
            labels={
                "revenue": "Revenue (£)",
                "Country": ""
            }
        )

        fig = style_chart(fig, 450)

        st.plotly_chart(fig, width="stretch")

    with right:

        st.subheader("Cancellation-to-Sales Ratio")

        fig = px.bar(
            cancellation.sort_values("cancellation_ratio"),
            x="cancellation_ratio",
            y="Country",
            orientation="h",
            color_discrete_sequence=[ORANGE],
            labels={
                "cancellation_ratio": "Cancellation-to-sales (%)",
                "Country": ""
            }
        )

        fig = style_chart(fig, 450)

        st.plotly_chart(fig, width="stretch")

    st.info(
        "Cancellation-to-sales ratio is cancellation value divided by "
        "sales value. It is not the percentage of invoices cancelled."
    )

    st.subheader("Country Revenue Details")

    st.dataframe(
        countries,
        width="stretch",
        hide_index=True
    )


# --------------------------------------------------
# 12. PRODUCT ANALYSIS PAGE
# --------------------------------------------------

elif page == "Product Analysis":

    st.title("Product Intelligence")

    st.caption(
        "Identify top-selling products and products with high cancellation value."
    )

    left, right = st.columns(2)

    with left:

        st.subheader("Top Selling Products")

        fig = px.bar(
            products.sort_values("sales"),
            x="sales",
            y="Description",
            orientation="h",
            color_discrete_sequence=[PRIMARY],
            labels={
                "sales": "Sales (£)",
                "Description": ""
            }
        )

        fig = style_chart(fig, 550)

        st.plotly_chart(fig, width="stretch")

    with right:

        st.subheader("Products with Highest Cancellation Value")

        fig = px.bar(
            returned_products.sort_values("cancellation_value"),
            x="cancellation_value",
            y="Description",
            orientation="h",
            color_discrete_sequence=[ORANGE],
            labels={
                "cancellation_value": "Cancellation Value (£)",
                "Description": ""
            }
        )

        fig = style_chart(fig, 550)

        st.plotly_chart(fig, width="stretch")

    st.divider()

    st.subheader("Product Sales Details")

    st.dataframe(
        products,
        width="stretch",
        hide_index=True
    )


# --------------------------------------------------
# 13. CUSTOMER INSIGHTS PAGE
# --------------------------------------------------

elif page == "Customer Insights":

    st.title("Customer Intelligence")

    st.caption(
        "Understand customer purchasing behaviour using RFM segmentation."
    )

    st.info(
        "RFM analysis includes all identified customers and is independent "
        "of the selected country filter."
    )

    total_customers = len(rfm)

    segment_counts = (
        rfm["segment"]
        .value_counts()
        .rename_axis("segment")
        .reset_index(name="customers")
    )

    at_risk = rfm[
        rfm["segment"].isin(["At Risk", "Hibernating"])
    ].shape[0]

    champions = rfm[
        rfm["segment"] == "Champions"
    ].shape[0]

    c1, c2, c3 = st.columns(3)

    c1.metric("Identified Customers", f"{total_customers:,}")

    c2.metric("At Risk + Hibernating", f"{at_risk:,}")

    c3.metric("Champions", f"{champions:,}")

    st.divider()

    left, right = st.columns(2)

    with left:

        st.subheader("Customer Distribution")

        fig = px.pie(
            segment_counts,
            names="segment",
            values="customers",
            hole=0.55,
            color_discrete_sequence=px.colors.qualitative.Set2
        )

        fig = style_chart(fig, 420)

        st.plotly_chart(fig, width="stretch")

    with right:

        st.subheader("Customers by Segment")

        fig = px.bar(
            segment_counts.sort_values("customers"),
            x="customers",
            y="segment",
            orientation="h",
            color_discrete_sequence=[PRIMARY],
            labels={
                "customers": "Number of Customers",
                "segment": ""
            }
        )

        fig = style_chart(fig, 420)

        st.plotly_chart(fig, width="stretch")

    st.divider()

    st.subheader("Top 10 Customers by Monetary Value")

    top_customers = (
        rfm.sort_values("monetary", ascending=False)
        .head(10)
        .copy()
    )

    if "Customer ID" in top_customers.columns:
        top_customers["Customer ID"] = (
            top_customers["Customer ID"].astype(str)
        )

    st.dataframe(
        top_customers,
        width="stretch",
        hide_index=True
    )

    st.caption(
        "Monetary value is based on positive sales value, not "
        "cancellation-adjusted revenue."
    )


# --------------------------------------------------
# 14. MARKET BASKET PAGE
# --------------------------------------------------

elif page == "Market Basket":

    st.title("Market Basket Analysis")

    st.caption(
        "Discover products that customers frequently purchase together."
    )

    if basket.empty:

        st.warning(
            "Association rules not found. Run "
            "python scripts/market_basket_analysis.py first."
        )

    else:

        st.markdown(
            """
            Market Basket Analysis uses association rules to identify
            relationships between products. These relationships can help
            inform product bundling and recommendation experiments.
            """
        )

        required_columns = {
            "antecedents",
            "consequents",
            "support",
            "confidence",
            "lift"
        }

        if required_columns.issubset(basket.columns):

            best_rule = basket.sort_values(
                "lift",
                ascending=False
            ).iloc[0]

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Top Rule Support",
                f"{best_rule['support']:.2%}"
            )

            c2.metric(
                "Confidence",
                f"{best_rule['confidence']:.2%}"
            )

            c3.metric(
                "Lift",
                f"{best_rule['lift']:.2f}"
            )

            st.divider()

            st.subheader("Top Product Association Rules")

            display_rules = basket.sort_values(
                "lift",
                ascending=False
            ).head(15)

            st.dataframe(
                display_rules,
                width="stretch",
                hide_index=True
            )

            st.info(
                "Lift above 1 indicates a positive association in the "
                "analysed baskets. Association does not prove causation."
            )

        else:

            st.warning(
                "The association rules CSV does not contain the expected "
                "columns: antecedents, consequents, support, confidence, lift."
            )


# --------------------------------------------------
# 15. FOOTER
# --------------------------------------------------

st.divider()

st.markdown(
    """
    <div style="text-align:center; color:#64748B; padding:12px;">
        <b>RevenueLeak</b> · Retail Revenue Intelligence Platform<br>
        <span style="font-size:12px;">
            Built with Python · Streamlit · DuckDB · Plotly
        </span>
    </div>
    """,
    unsafe_allow_html=True
)

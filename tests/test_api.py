
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert "RevenueLeak" in response.json()["message"]


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_overview():
    response = client.get("/api/overview")

    assert response.status_code == 200

    data = response.json()

    assert abs(data["total_sales"] - 20476260.45) < 0.01
    assert abs(data["cancellation_value"] - 1462424.18) < 0.01
    assert abs(data["net_gross_revenue"] - 19013836.27) < 0.01


def test_monthly_revenue():
    response = client.get("/api/monthly-revenue")

    assert response.status_code == 200
    assert len(response.json()) > 0
    assert "month" in response.json()[0]


def test_countries():
    response = client.get("/api/countries")

    assert response.status_code == 200
    assert len(response.json()) > 0
    assert "Country" in response.json()[0]


def test_top_products():
    response = client.get("/api/products/top?limit=10")

    assert response.status_code == 200
    assert len(response.json()) <= 10


def test_cancelled_products():
    response = client.get("/api/products/cancellations?limit=10")

    assert response.status_code == 200
    assert len(response.json()) <= 10


def test_customer_segments():
    response = client.get("/api/customers/segments")

    assert response.status_code == 200

    data = response.json()
    total_customers = sum(item["customers"] for item in data)

    assert total_customers == 5878


def test_top_customers():
    response = client.get("/api/customers/top?limit=10")

    assert response.status_code == 200
    assert len(response.json()) == 10
    assert response.json()[0]["monetary"] >= response.json()[-1]["monetary"]


def test_country_filter():
    response = client.get("/api/overview?country=United%20Kingdom")

    assert response.status_code == 200

    data = response.json()
    assert abs(data["net_gross_revenue"] - 16144362.91) < 0.01

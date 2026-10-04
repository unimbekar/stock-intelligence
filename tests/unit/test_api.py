from fastapi.testclient import TestClient
from meridian_api.main import create_app


def test_health_and_meta() -> None:
    client = TestClient(create_app())
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.headers["x-content-type-options"] == "nosniff"

    meta = client.get("/api/v1/meta")
    assert meta.status_code == 200
    body = meta.json()
    assert body["dataMode"] == "mock"
    assert body["dataModeLabel"] == "DEMO DATA"
    assert body["target"]["requiredReturnPercent"] == 4.0
    assert "does not provide personalized investment advice" in body["disclaimer"]


def test_quote_is_labeled_mock_and_unknown_ticker_is_404() -> None:
    client = TestClient(create_app())
    quote = client.get("/api/v1/market/quotes/nvda")
    assert quote.status_code == 200
    payload = quote.json()
    assert payload["ticker"] == "NVDA"
    assert payload["dataMode"] == "mock"
    assert payload["price"] == "178.40"

    missing = client.get("/api/v1/market/quotes/ZZZZ")
    assert missing.status_code == 404

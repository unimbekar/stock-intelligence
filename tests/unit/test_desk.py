from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

from meridian_analytics.ledger import Fill
from meridian_analytics.scoring import IdeaFilters, ScoreInput, rank
from meridian_analytics.snapshot import cash_delta, holding_rating, opening_cash
from meridian_api.ideas_service import search_ideas
from meridian_api.mail import deliverable, describe_alert
from meridian_api.portfolio_view import percent_target, plan_holding_change, price_crossed
from meridian_config.product import load_product
from meridian_market.catalog import get_catalog


def _item(ticker: str, price: float = 100) -> ScoreInput:
    return ScoreInput(
        ticker=ticker,
        company=ticker,
        price=price,
        market_cap=1_000_000_000_000,
        volume=10_000_000,
        sector="Technology",
        categories=("AI",),
        rsi=55,
        sma20=price - 1,
        sma50=price - 2,
        sma200=price - 3,
        relative_volume=1.3,
        atr=2,
        annualized_vol=0.3,
        revenue_growth=0.2,
        eps_growth=0.15,
        operating_margin=0.25,
        roe=0.2,
        pe=22,
        analyst="Buy",
        next_earnings=None,
        as_of=date(2026, 10, 2),
        sector_return=0.02,
    )


def test_rank_returns_five_when_five_or_more_pass() -> None:
    items = [_item(ticker) for ticker in ["A", "B", "C", "D", "E", "F", "G"]]
    rows = rank(items, IdeaFilters(), load_product().scoring_weights.as_fractions(), limit=5)
    assert len(rows) == 5


def test_rank_does_not_invent_names_when_fewer_match() -> None:
    items = [_item("NVDA"), _item("AMD")]
    rows = rank(items, IdeaFilters(categories=("Healthcare",)), load_product().scoring_weights.as_fractions())
    assert rows == []


def test_opening_cash_reverses_seed_buys() -> None:
    fills = [
        Fill("NVDA", "buy", Decimal("20"), Decimal("160")),
        Fill("MSFT", "buy", Decimal("10"), Decimal("410")),
        Fill("LLY", "buy", Decimal("5"), Decimal("780")),
    ]
    assert opening_cash(Decimal("38800"), fills) == Decimal("50000")
    assert cash_delta("buy", Decimal("20"), Decimal("160"), Decimal("0")) == Decimal("-3200")


def test_ideas_from_demo_book_are_at_most_five() -> None:
    result = search_ideas(
        get_catalog(),
        amount=Decimal("50000"),
        style="swing",
        risk="moderate",
        filters=IdeaFilters(),
        weights=load_product().scoring_weights.as_fractions(),
    )
    ideas = result["ideas"]
    assert isinstance(ideas, list)
    assert 1 <= len(ideas) <= 5
    assert len({idea["ticker"] for idea in ideas}) == len(ideas)


def test_editing_a_holding_refunds_the_old_cost_basis() -> None:
    bought = SimpleNamespace(
        ticker="AAPL",
        side="buy",
        quantity=Decimal("10"),
        price=Decimal("100"),
        fees=Decimal("0"),
        executed_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    portfolio = SimpleNamespace(transactions=[bought], cash=Decimal("500"))
    delta, orders = plan_holding_change(portfolio, "aapl", Decimal("4"), Decimal("50"))
    assert delta == Decimal("800")
    assert [order["side"] for order in orders] == ["sell", "buy"]
    assert orders[1]["quantity"] == Decimal("4")
    removed, _orders = plan_holding_change(portfolio, "AAPL", Decimal("0"), Decimal("0"))
    assert removed == Decimal("1000")


def test_holding_rating_uses_price_and_filed_growth() -> None:
    assert (
        holding_rating(
            price=100,
            sma20=90,
            sma50=80,
            rsi=55,
            eps_growth=0.2,
            revenue_growth=0.1,
            pe=18,
        )
        == "Buy"
    )
    assert (
        holding_rating(
            price=70,
            sma20=90,
            sma50=100,
            rsi=80,
            eps_growth=-0.2,
            revenue_growth=-0.1,
            pe=60,
        )
        == "Sell"
    )
    assert (
        holding_rating(
            price=100,
            sma20=None,
            sma50=None,
            rsi=None,
            eps_growth=None,
            revenue_growth=None,
            pe=None,
        )
        == "Hold"
    )


def test_percent_alert_is_the_saved_price_moved_by_that_percent() -> None:
    assert percent_target(Decimal("100"), Decimal("5"), "above") == Decimal("105.00")
    assert percent_target(Decimal("233.95"), Decimal("5"), "below") == Decimal("222.25")
    assert price_crossed(Decimal("105"), Decimal("105.00"), "above")
    assert price_crossed(Decimal("104.99"), Decimal("105.00"), "above") is False
    assert deliverable("demo@meridian.local") is False
    assert deliverable("trader@gmail.com") is True
    quote = SimpleNamespace(price=Decimal("105.00"), as_of=date(2026, 10, 2))
    alert = SimpleNamespace(
        ticker="NVDA",
        alert_type="percent",
        params={"direction": "above", "percent": 5, "basis": "100.00", "target": "105.00"},
    )
    subject, body = describe_alert(alert, quote)
    assert "5% above $100.00 ($105.00)" in subject
    assert "105.00" in body
    assert "not a recommendation" in body

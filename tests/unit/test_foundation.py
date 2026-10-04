from datetime import date
from decimal import Decimal

import pytest
from meridian_ai.provider import AIMessage, grounded_summary, numbers_not_in_source
from meridian_analytics.ledger import Fill, apply_fills, unrealized_pnl
from meridian_analytics.performance import expectancy, max_drawdown, profit_factor, sharpe, win_rate
from meridian_api.passwords import hash_password, verify_password
from meridian_config.product import load_product
from meridian_market.catalog import Catalog
from meridian_market.indicators import rsi, sma
from meridian_market.universe import UNIVERSE
from meridian_research.providers import bundle_for
from meridian_trading.sizing import daily_loss_status, plan_position, required_return


def test_required_return_is_four_percent() -> None:
    assert required_return(Decimal("50000"), Decimal("2000")) == Decimal("4.00")


def test_position_size_example() -> None:
    plan = plan_position(
        account=Decimal("50000"),
        risk_percent=Decimal("1"),
        entry=Decimal("200"),
        stop=Decimal("195"),
        target=Decimal("215"),
    )
    assert plan.max_risk == Decimal("500.00")
    assert plan.risk_per_share == Decimal("5.00")
    assert plan.shares == Decimal("100")
    assert plan.position_value == Decimal("20000.00")
    assert plan.risk_reward == Decimal("3.00")


def test_position_size_rejects_long_stop_above_entry() -> None:
    with pytest.raises(ValueError):
        plan_position(
            account=Decimal("50000"),
            risk_percent=Decimal("1"),
            entry=Decimal("200"),
            stop=Decimal("205"),
        )


def test_daily_loss_limit_message() -> None:
    assert daily_loss_status(Decimal("1000"), Decimal("1000")) == "Daily risk limit reached."
    assert daily_loss_status(Decimal("999"), Decimal("1000")) == "Within daily loss limit."


def test_average_cost_and_realized_pnl() -> None:
    book = apply_fills(
        [
            Fill("NVDA", "buy", Decimal("10"), Decimal("100"), Decimal("10")),
            Fill("NVDA", "buy", Decimal("10"), Decimal("120"), Decimal("0")),
            Fill("NVDA", "sell", Decimal("10"), Decimal("130"), Decimal("5")),
        ]
    )
    position = book["NVDA"]
    assert position.quantity == Decimal("10")
    assert position.average_cost == Decimal("110.5")
    assert position.realized_pnl == Decimal("190")
    assert unrealized_pnl(position, Decimal("121")) == Decimal("105")


def test_short_cover() -> None:
    book = apply_fills(
        [
            Fill("TSLA", "short", Decimal("4"), Decimal("250")),
            Fill("TSLA", "cover", Decimal("4"), Decimal("230"), Decimal("2")),
        ]
    )
    assert book["TSLA"].quantity == Decimal("0")
    assert book["TSLA"].realized_pnl == Decimal("78")


def test_sma_and_rsi_bounds() -> None:
    assert sma([1, 2, 3, 4, 5], 3) == [None, None, 2, 3, 4]
    rising = [float(value) for value in range(1, 30)]
    assert rsi(rising)[-1] == 100


def test_drawdown_and_trade_stats() -> None:
    assert max_drawdown([Decimal("100"), Decimal("120"), Decimal("90")]) == Decimal("-0.25")
    trades = [Decimal("100"), Decimal("-50"), Decimal("20")]
    assert win_rate(trades) == pytest.approx(2 / 3)
    assert profit_factor(trades) == pytest.approx(2.4)
    assert expectancy(trades) == Decimal("70") / Decimal("3")
    assert sharpe([Decimal("0.01"), Decimal("0.01")]) is None


def test_weights_sum_to_one() -> None:
    weights = load_product().scoring_weights.as_fractions()
    assert sum(weights.values()) == pytest.approx(1)


def test_demo_universe_is_pinned_to_anchors() -> None:
    catalog = Catalog(as_of=date(2026, 10, 4))
    assert len(UNIVERSE) == 15
    assert {item.ticker for item in UNIVERSE} >= {
        "NVDA",
        "AMD",
        "MSFT",
        "AAPL",
        "AMZN",
        "GOOGL",
        "META",
        "TSLA",
        "AVGO",
        "PLTR",
        "JPM",
        "LLY",
        "NFLX",
        "COST",
        "CRWD",
    }
    for item in UNIVERSE:
        assert catalog.bars(item.ticker)[-1].close == item.anchor_price
        assert catalog.quote(item.ticker).price == item.anchor_price
        bundle = bundle_for(item.ticker, catalog)
        assert bundle.consensus.ticker == item.ticker
        assert all(evidence.synthetic for evidence in bundle.items)
        disclosure = bundle.items[0].disclosure.lower()
        summary = bundle.items[0].summary.lower()
        assert "not" in summary or "not" in disclosure


def test_password_round_trip() -> None:
    stored = hash_password("meridian-demo")
    assert verify_password("meridian-demo", stored)
    assert not verify_password("wrong", stored)


def test_explainer_does_not_invent_numbers() -> None:
    text = grounded_summary(
        [AIMessage("user", "What is the price?")],
        {"get_stock_quote": {"ticker": "NVDA", "price": "178.40"}},
    )
    assert "178.40" in text
    assert numbers_not_in_source("The price is 999", "178.40") == {"999"}

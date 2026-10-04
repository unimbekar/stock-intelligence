"""Deterministic demo price paths. The last close is the anchor, by construction."""

from __future__ import annotations

import math
import random
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from meridian_market.models import Bar

MONEY = Decimal("0.01")
SESSION_COUNT = 320


def last_weekday(on: date) -> date:
    day = on
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def trading_days(end: date, count: int) -> list[date]:
    days: list[date] = []
    cursor = end
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= timedelta(days=1)
    days.reverse()
    return days


def _money(value: float) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def build_bars(
    *,
    anchor: Decimal,
    start: Decimal,
    annualized_vol: float,
    seed: int,
    end: date,
    sessions: int = SESSION_COUNT,
    base_volume: int = 1_000_000,
) -> list[Bar]:
    if anchor <= 0 or start <= 0:
        raise ValueError("prices must be positive")
    days = trading_days(end, sessions)
    daily_vol = annualized_vol / math.sqrt(252)
    rng = random.Random(seed)
    noises = [rng.gauss(0.0, daily_vol) for _ in days]
    target = math.log(float(anchor) / float(start))
    drift = (target - sum(noises)) / len(days)

    closes: list[float] = []
    price = float(start)
    for noise in noises:
        price = max(0.5, price * math.exp(drift + noise))
        closes.append(price)
    # Pin the final close to the published anchor so quotes stay stable.
    scale = float(anchor) / closes[-1]
    closes = [value * scale for value in closes]

    bars: list[Bar] = []
    previous = float(start)
    for index, (session, close) in enumerate(zip(days, closes, strict=True)):
        open_ = previous if index else float(start) * scale
        wiggle = abs(rng.gauss(0.0, daily_vol)) * close
        high = max(open_, close) + wiggle
        low = max(0.5, min(open_, close) - wiggle * 0.85)
        volume_noise = 0.75 + rng.random() * 0.7
        volume = max(1, int(base_volume * volume_noise))
        bars.append(
            Bar(
                session=session,
                open=_money(open_),
                high=_money(high),
                low=_money(low),
                close=_money(close),
                volume=volume,
            )
        )
        previous = close
    bars[-1] = bars[-1].model_copy(update={"close": anchor.quantize(MONEY)})
    if bars[-1].high < bars[-1].close:
        bars[-1] = bars[-1].model_copy(update={"high": bars[-1].close})
    if bars[-1].low > bars[-1].close:
        bars[-1] = bars[-1].model_copy(update={"low": bars[-1].close})
    return bars

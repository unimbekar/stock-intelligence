from __future__ import annotations

import math
from decimal import Decimal


def _floats(values: list[Decimal] | list[float]) -> list[float]:
    return [float(value) for value in values]


def win_rate(trade_pnls: list[Decimal]) -> float | None:
    if not trade_pnls:
        return None
    wins = sum(1 for value in trade_pnls if value > 0)
    return wins / len(trade_pnls)


def profit_factor(trade_pnls: list[Decimal]) -> float | None:
    gross_win = sum((value for value in trade_pnls if value > 0), Decimal("0"))
    gross_loss = sum((-value for value in trade_pnls if value < 0), Decimal("0"))
    if gross_loss == 0:
        return None if gross_win == 0 else math.inf
    return float(gross_win / gross_loss)


def expectancy(trade_pnls: list[Decimal]) -> Decimal | None:
    if not trade_pnls:
        return None
    return sum(trade_pnls, Decimal("0")) / Decimal(len(trade_pnls))


def drawdown(equity: list[Decimal]) -> list[Decimal]:
    peak = Decimal("-1e100")
    series: list[Decimal] = []
    for value in equity:
        peak = max(peak, value)
        if peak == 0:
            series.append(Decimal("0"))
        else:
            series.append((value - peak) / peak)
    return series


def max_drawdown(equity: list[Decimal]) -> Decimal | None:
    if not equity:
        return None
    return min(drawdown(equity))


def sharpe(returns: list[Decimal], periods_per_year: int = 252, risk_free: Decimal = Decimal("0")) -> float | None:
    series = _floats(returns)
    if len(series) < 2:
        return None
    excess = [value - float(risk_free) for value in series]
    mean = sum(excess) / len(excess)
    variance = sum((value - mean) ** 2 for value in excess) / (len(excess) - 1)
    deviation = math.sqrt(variance)
    if deviation == 0:
        return None
    return (mean / deviation) * math.sqrt(periods_per_year)


def sortino(returns: list[Decimal], periods_per_year: int = 252, risk_free: Decimal = Decimal("0")) -> float | None:
    series = _floats(returns)
    if len(series) < 2:
        return None
    excess = [value - float(risk_free) for value in series]
    mean = sum(excess) / len(excess)
    downside = [min(value, 0.0) ** 2 for value in excess]
    deviation = math.sqrt(sum(downside) / (len(downside) - 1))
    if deviation == 0:
        return None
    return (mean / deviation) * math.sqrt(periods_per_year)

"""Standard indicator math over a demo price series."""

from __future__ import annotations

import math


def sma(values: list[float], period: int) -> list[float | None]:
    if period < 1:
        raise ValueError("period must be positive")
    out: list[float | None] = []
    running = 0.0
    for index, value in enumerate(values):
        running += value
        if index >= period:
            running -= values[index - period]
        if index + 1 < period:
            out.append(None)
        else:
            out.append(running / period)
    return out


def ema(values: list[float], period: int) -> list[float | None]:
    if period < 1:
        raise ValueError("period must be positive")
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    k = 2 / (period + 1)
    previous = seed
    for index in range(period, len(values)):
        previous = values[index] * k + previous * (1 - k)
        out[index] = previous
    return out


def rsi(closes: list[float], period: int = 14) -> list[float | None]:
    if period < 1:
        raise ValueError("period must be positive")
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, period + 1):
        change = closes[index] - closes[index - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    out[period] = _rsi_value(avg_gain, avg_loss)
    for index in range(period + 1, len(closes)):
        change = closes[index] - closes[index - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[index] = _rsi_value(avg_gain, avg_loss)
    return out


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0 and avg_gain == 0:
        return 50.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(
    closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)
    line: list[float | None] = []
    for fast_value, slow_value in zip(fast_ema, slow_ema, strict=True):
        if fast_value is None or slow_value is None:
            line.append(None)
        else:
            line.append(fast_value - slow_value)
    present = [value for value in line if value is not None]
    signal_on_present = ema(present, signal)
    signal_line: list[float | None] = [None] * len(line)
    histogram: list[float | None] = [None] * len(line)
    cursor = 0
    for index, value in enumerate(line):
        if value is None:
            continue
        sig = signal_on_present[cursor]
        signal_line[index] = sig
        if sig is not None:
            histogram[index] = value - sig
        cursor += 1
    return line, signal_line, histogram


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[float | None]:
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("OHLC series must be the same length")
    true_ranges: list[float] = []
    for index, (high, low, _close) in enumerate(zip(highs, lows, closes, strict=True)):
        if index == 0:
            true_ranges.append(high - low)
            continue
        previous = closes[index - 1]
        true_ranges.append(max(high - low, abs(high - previous), abs(low - previous)))
    out: list[float | None] = [None] * len(closes)
    if len(true_ranges) < period:
        return out
    current = sum(true_ranges[:period]) / period
    out[period - 1] = current
    for index in range(period, len(true_ranges)):
        current = (current * (period - 1) + true_ranges[index]) / period
        out[index] = current
    return out


def relative_volume(volumes: list[float], period: int = 20) -> list[float | None]:
    averages = sma(volumes, period)
    out: list[float | None] = []
    for volume, average in zip(volumes, averages, strict=True):
        if average is None or average == 0:
            out.append(None)
        else:
            out.append(volume / average)
    return out


def round_or_none(value: float | None, digits: int = 4) -> float | None:
    if value is None or math.isnan(value):
        return None
    return round(value, digits)

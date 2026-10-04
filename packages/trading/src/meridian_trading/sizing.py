from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

MONEY = Decimal("0.01")
SHARES = Decimal("1")


@dataclass(frozen=True)
class PositionPlan:
    account: Decimal
    risk_percent: Decimal
    max_risk: Decimal
    entry: Decimal
    stop: Decimal
    target: Decimal | None
    risk_per_share: Decimal
    shares: Decimal
    position_value: Decimal
    reward_per_share: Decimal | None
    risk_reward: Decimal | None
    side: str


def required_return(capital: Decimal, daily_target: Decimal) -> Decimal:
    if capital <= 0:
        raise ValueError("capital must be positive")
    return ((daily_target / capital) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def plan_position(
    *,
    account: Decimal,
    risk_percent: Decimal,
    entry: Decimal,
    stop: Decimal,
    target: Decimal | None = None,
    side: str = "long",
) -> PositionPlan:
    if account <= 0:
        raise ValueError("account must be positive")
    if risk_percent <= 0 or risk_percent > 100:
        raise ValueError("risk percent must be between 0 and 100")
    if entry <= 0 or stop <= 0:
        raise ValueError("entry and stop must be positive")
    if side not in {"long", "short"}:
        raise ValueError("side must be long or short")
    if side == "long" and stop >= entry:
        raise ValueError("a long stop must be below the entry")
    if side == "short" and stop <= entry:
        raise ValueError("a short stop must be above the entry")

    risk_per_share = abs(entry - stop)
    max_risk = (account * risk_percent / Decimal("100")).quantize(MONEY, rounding=ROUND_HALF_UP)
    shares = (max_risk / risk_per_share).to_integral_value(rounding=ROUND_DOWN)
    reward_per_share: Decimal | None = None
    risk_reward: Decimal | None = None
    if target is not None:
        if target <= 0:
            raise ValueError("target must be positive")
        if side == "long" and target <= entry:
            raise ValueError("a long target must be above the entry")
        if side == "short" and target >= entry:
            raise ValueError("a short target must be below the entry")
        reward_per_share = abs(target - entry)
        risk_reward = (reward_per_share / risk_per_share).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return PositionPlan(
        account=account,
        risk_percent=risk_percent,
        max_risk=max_risk,
        entry=entry,
        stop=stop,
        target=target,
        risk_per_share=risk_per_share.quantize(MONEY, rounding=ROUND_HALF_UP),
        shares=shares,
        position_value=(shares * entry).quantize(MONEY, rounding=ROUND_HALF_UP),
        reward_per_share=(
            None if reward_per_share is None else reward_per_share.quantize(MONEY, rounding=ROUND_HALF_UP)
        ),
        risk_reward=risk_reward,
        side=side,
    )


def daily_loss_status(loss: Decimal, limit: Decimal) -> str:
    if limit <= 0:
        raise ValueError("daily loss limit must be positive")
    if loss < 0:
        raise ValueError("loss is expressed as a positive amount")
    if loss >= limit:
        return "Daily risk limit reached."
    return "Within daily loss limit."

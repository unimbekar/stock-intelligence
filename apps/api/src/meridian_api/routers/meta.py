from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter
from meridian_config.product import load_product
from meridian_config.settings import get_settings
from meridian_trading.sizing import required_return

from meridian_api.gateway import data_status

router = APIRouter(prefix="/api/v1")


@router.get("/meta")
def meta() -> dict[str, object]:
    settings = get_settings()
    product = load_product()
    status = data_status()
    capital = Decimal(str(product.target_scenario.capital))
    target = Decimal(str(product.target_scenario.daily_profit_target))
    return {
        "name": product.name,
        "tagline": product.tagline,
        "dataMode": status["dataMode"],
        "dataModeLabel": status["dataModeLabel"],
        "dataWarning": status["warning"],
        "source": status["source"],
        "aiProvider": settings.ai_provider,
        "disclaimer": product.disclaimer,
        "target": {
            "capital": float(capital),
            "dailyProfitTarget": float(target),
            "requiredReturnPercent": float(required_return(capital, target)),
            "note": product.target_scenario.note,
        },
        "scoringWeights": product.scoring_weights.model_dump(by_alias=True),
    }

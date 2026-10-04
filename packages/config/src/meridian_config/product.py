from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


class TargetScenario(BaseModel):
    capital: float
    daily_profit_target: float = Field(alias="dailyProfitTarget")
    note: str

    model_config = {"populate_by_name": True}


class ScoringWeights(BaseModel):
    technical_momentum: float = Field(alias="technicalMomentum")
    fundamental_strength: float = Field(alias="fundamentalStrength")
    analyst_sentiment: float = Field(alias="analystSentiment")
    earnings_momentum: float = Field(alias="earningsMomentum")
    valuation: float
    sector_momentum: float = Field(alias="sectorMomentum")
    risk_volatility: float = Field(alias="riskVolatility")

    model_config = {"populate_by_name": True}

    def as_fractions(self) -> dict[str, float]:
        return {
            "technical_momentum": self.technical_momentum,
            "fundamental_strength": self.fundamental_strength,
            "analyst_sentiment": self.analyst_sentiment,
            "earnings_momentum": self.earnings_momentum,
            "valuation": self.valuation,
            "sector_momentum": self.sector_momentum,
            "risk_volatility": self.risk_volatility,
        }


class ProductConfig(BaseModel):
    name: str
    tagline: str
    data_mode_label: str = Field(alias="dataModeLabel")
    disclaimer: str
    target_scenario: TargetScenario = Field(alias="targetScenario")
    scoring_weights: ScoringWeights = Field(alias="scoringWeights")

    model_config = {"populate_by_name": True}


def _candidate_paths() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        here.with_name("product.json"),
        here.parents[2] / "product.json",
        Path.cwd() / "packages" / "config" / "product.json",
    ]


@lru_cache(maxsize=1)
def load_product() -> ProductConfig:
    for path in _candidate_paths():
        if path.is_file():
            return ProductConfig.model_validate(json.loads(path.read_text()))
    raise FileNotFoundError("product.json was not found in the config package")

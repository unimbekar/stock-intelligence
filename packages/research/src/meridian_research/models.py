from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


def _camel(name: str) -> str:
    head, *tail = name.split("_")
    return head + "".join(part.capitalize() for part in tail)


class Model(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True)


class EvidenceItem(Model):
    id: str
    ticker: str
    source: str
    source_type: str
    title: str
    published_on: date
    author: str | None = None
    rating: str | None = None
    price_target: float | None = None
    summary: str
    url: str | None = None
    data_mode: str = "mock"
    synthetic: bool = True
    disclosure: str = "Synthetic demonstration item. It was not retrieved from the named publication."


class AnalystConsensus(Model):
    ticker: str
    consensus: str
    buy: int
    hold: int
    sell: int
    average_target: float
    high_target: float
    low_target: float
    upside_percent: float
    data_mode: str = "mock"
    disclosure: str = "Illustrative demo consensus. Not a live analyst feed."


class EvidenceBundle(Model):
    ticker: str
    items: list[EvidenceItem] = Field(default_factory=list)
    consensus: AnalystConsensus
    data_mode: str = "mock"

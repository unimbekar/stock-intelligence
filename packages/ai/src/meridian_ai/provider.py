from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Protocol

import httpx
from meridian_config.settings import Settings


@dataclass
class AIMessage:
    role: str
    content: str


@dataclass
class AIResponse:
    content: str
    provider: str
    model: str
    used_tools: list[str] = field(default_factory=list)
    grounded: bool = True


class AIProvider(Protocol):
    name: str

    def complete(
        self,
        messages: list[AIMessage],
        tool_results: dict[str, object],
    ) -> AIResponse: ...


_NUMBER = re.compile(r"\d+(?:\.\d+)?")


class LocalAIProvider:
    """Uses a local OpenAI-compatible server when configured.

    Without a model, it restates tool results and refuses to introduce numbers
    that are not already in those results.
    """

    name = "local"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def complete(
        self,
        messages: list[AIMessage],
        tool_results: dict[str, object],
    ) -> AIResponse:
        model = self.settings.local_ai_model.strip()
        if not model:
            return AIResponse(
                content=readable_note(messages, tool_results),
                provider=self.name,
                model="offline-explainer",
                used_tools=list(tool_results),
            )
        question = next((message.content for message in reversed(messages) if message.role == "user"), "")
        payload = {
            "model": model,
            "stream": False,
            "think": False,
            "options": {"temperature": 0.2, "num_predict": 700},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Meridian's research assistant on this machine. "
                        "Answer only from the JSON records below. "
                        "If a figure is absent, say it is unavailable. "
                        "Do not invent quotes, analyst targets, filings, or returns. "
                        "Write a short research note in plain sentences. "
                        "Name the source of each figure, which is Nasdaq or SEC EDGAR."
                    ),
                },
                {
                    "role": "user",
                    "content": "Question: "
                    + question
                    + "\n\nRecords:\n"
                    + json.dumps(tool_results, default=str),
                },
            ],
        }
        content = _ollama_chat(self.settings.local_ai_base_url, payload)
        source = json.dumps(tool_results, default=str) + question
        if not content:
            content = "The local model did not respond. " + readable_note(messages, tool_results)
        elif numbers_not_in_source(content, source):
            content = (
                "The local model introduced figures that were not in the retrieved records. "
                "This note uses those records directly.\n\n" + readable_note(messages, tool_results)
            )
        return AIResponse(
            content=content,
            provider=self.name,
            model=model,
            used_tools=list(tool_results),
        )


class _UnconfiguredProvider:
    def __init__(self, name: str) -> None:
        self.name = name

    def complete(
        self,
        messages: list[AIMessage],
        tool_results: dict[str, object],
    ) -> AIResponse:
        raise RuntimeError(
            f"AI provider '{self.name}' is not configured. Set AI_PROVIDER=local "
            "or supply that provider's credentials on the server."
        )


class OpenAIProvider(_UnconfiguredProvider):
    def __init__(self) -> None:
        super().__init__("openai")


class AnthropicProvider(_UnconfiguredProvider):
    def __init__(self) -> None:
        super().__init__("anthropic")


class AWSBedrockProvider(_UnconfiguredProvider):
    def __init__(self) -> None:
        super().__init__("bedrock")


def build_provider(settings: Settings) -> AIProvider:
    if settings.ai_provider == "local":
        return LocalAIProvider(settings)
    if settings.ai_provider == "openai":
        return OpenAIProvider()
    if settings.ai_provider == "anthropic":
        return AnthropicProvider()
    return AWSBedrockProvider()


def _ollama_chat(base_url: str, payload: dict) -> str:
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3]
    try:
        response = httpx.post(root + "/api/chat", json=payload, timeout=180)
        response.raise_for_status()
        message = response.json().get("message") or {}
        content = str(message.get("content") or "").strip()
        if content:
            return content
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return ""
    return ""


def readable_note(messages: list[AIMessage], tool_results: dict[str, object]) -> str:
    question = next((message.content for message in reversed(messages) if message.role == "user"), "")
    if not tool_results:
        return f"No records were retrieved, so there is no quote or filing to report. Question: {question}".strip()
    lines = ["Research note from retrieved records only."]
    if question:
        lines.append(f"Question: {question}")
    quote = tool_results.get("get_stock_quote")
    if isinstance(quote, dict) and quote.get("price") is not None:
        lines.append(
            f"{quote.get('ticker')} {quote.get('name')} closed at {quote.get('price')} "
            f"on {quote.get('asOf')} ({quote.get('change')} , {quote.get('changePercent')}%). "
            f"Volume {quote.get('volume')}. Source {quote.get('source') or 'connected book'}."
        )
    technicals = tool_results.get("get_technical_indicators")
    if isinstance(technicals, dict):
        lines.append(
            f"RSI {technicals.get('rsi')}. SMA20 {technicals.get('sma20')}. "
            f"SMA50 {technicals.get('sma50')}. SMA200 {technicals.get('sma200')}. ATR {technicals.get('atr')}."
        )
    facts = tool_results.get("get_fundamentals")
    if isinstance(facts, dict):
        lines.append(
            f"Fundamentals source {facts.get('source')}. Revenue {facts.get('revenue')}. "
            f"EPS {facts.get('eps')}. P/E {facts.get('pe')}. Operating margin {facts.get('operatingMargin')}."
        )
    research = tool_results.get("get_research")
    if isinstance(research, list):
        for item in research[:8]:
            if not isinstance(item, dict):
                continue
            link = f" {item.get('url')}" if item.get("url") else ""
            lines.append(f"{item.get('source')}: {item.get('title')}. {item.get('summary')}{link}")
    ratings = tool_results.get("get_analyst_ratings")
    if isinstance(ratings, dict) and ratings.get("disclosure"):
        lines.append(str(ratings["disclosure"]))
    portfolio = tool_results.get("get_portfolio")
    if isinstance(portfolio, dict) and portfolio.get("equity") is not None:
        lines.append(
            f"Paper equity {portfolio.get('equity')}. Cash {portfolio.get('cash')}. "
            f"Daily P&L {portfolio.get('dailyPnl')}."
        )
    text = "\n".join(lines)
    source = json.dumps({"question": question, "tools": tool_results}, default=str)
    if numbers_not_in_source(text, source):
        return grounded_summary(messages, tool_results)
    return text


def grounded_summary(messages: list[AIMessage], tool_results: dict[str, object]) -> str:
    question = next((message.content for message in reversed(messages) if message.role == "user"), "")
    if not tool_results:
        return (
            f"No tool results were supplied, so I will not quote a price, target, or filing. Question noted: {question}"
        ).strip()
    lines = [
        "This answer only restates tool results already retrieved by the application.",
        f"Question: {question}" if question else "Question: (none)",
    ]
    rendered_tools = {name: json.dumps(payload, default=str, sort_keys=True) for name, payload in tool_results.items()}
    for name, rendered in rendered_tools.items():
        lines.append(f"{name}: {rendered}")
    text = "\n".join(lines)
    source = json.dumps({"question": question, "tools": rendered_tools}, default=str)
    leaked = numbers_not_in_source(text, source)
    if leaked:
        raise AssertionError(f"explainer introduced numbers absent from tools: {sorted(leaked)}")
    return text


def numbers_not_in_source(text: str, source: str) -> set[str]:
    source_numbers = set(_NUMBER.findall(source))
    return {number for number in _NUMBER.findall(text) if number not in source_numbers}

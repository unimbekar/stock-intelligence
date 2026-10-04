from decimal import Decimal

from meridian_market.live import parse_nasdaq_rows
from meridian_market.sec import annual_series, build_fundamentals, parse_filings
from meridian_market.symbols import Listing, SymbolDirectory, mentioned_symbols, parse_company_tickers


def test_nasdaq_rows_parse_the_latest_session_first() -> None:
    bars = parse_nasdaq_rows(
        [
            {
                "date": "10/02/2026",
                "close": "$333.69",
                "open": "$333.26",
                "high": "$334.54",
                "low": "$330.61",
                "volume": "33,278,550",
            },
            {
                "date": "10/01/2026",
                "close": "$330.32",
                "open": "$330.00",
                "high": "$332.48",
                "low": "$325.81",
                "volume": "36,306,350",
            },
        ]
    )
    assert bars[-1].session.isoformat() == "2026-10-02"
    assert bars[-1].close == Decimal("333.69")
    assert bars[-1].volume == 33278550


def test_annual_series_prefers_the_concept_with_the_newer_filing() -> None:
    facts = {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {"USD": [{"end": "2022-01-30", "val": 10, "form": "10-K", "fp": "FY"}]}
            },
            "Revenues": {
                "units": {"USD": [{"end": "2026-01-25", "val": 90, "form": "10-K", "fp": "FY"}]}
            },
        }
    }
    series = annual_series(facts, ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"), "USD")
    assert series[-1] == ("2026-01-25", 90.0)


def test_annual_series_keeps_the_latest_10k() -> None:
    facts = {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"end": "2023-12-31", "val": 100, "form": "10-K", "fp": "FY"},
                        {"end": "2024-12-31", "val": 80, "form": "10-Q", "fp": "Q3"},
                        {"end": "2024-12-31", "val": 140, "form": "10-K", "fp": "FY"},
                    ]
                }
            }
        }
    }
    assert annual_series(facts, ("Revenues",), "USD") == [("2023-12-31", 100.0), ("2024-12-31", 140.0)]


def test_sec_fundamentals_omit_pe_without_a_market_price() -> None:
    facts = {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"end": "2023-12-31", "val": 100, "form": "10-K", "fp": "FY"},
                        {"end": "2024-12-31", "val": 150, "form": "10-K", "fp": "FY"},
                    ]
                }
            },
            "EarningsPerShareDiluted": {
                "units": {
                    "USD/shares": [
                        {"end": "2023-12-31", "val": 2, "form": "10-K", "fp": "FY"},
                        {"end": "2024-12-31", "val": 3, "form": "10-K", "fp": "FY"},
                    ]
                }
            },
        }
    }
    row = build_fundamentals("AAPL", facts, price=None)
    assert row is not None
    assert row.pe is None
    assert row.revenue == 150
    assert row.revenue_growth == 0.5
    assert row.source == "sec-edgar"
    priced = build_fundamentals("AAPL", facts, price=Decimal("30"))
    assert priced is not None
    assert priced.pe == 10.0


def test_symbol_search_finds_a_ticker_and_a_company_name() -> None:
    payload = {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": 1341439, "ticker": "ORCL", "title": "ORACLE CORP"},
    }
    directory = SymbolDirectory(parse_company_tickers(payload))
    assert directory.search("aapl")[0] == Listing("AAPL", "Apple Inc.", "0000320193")
    assert directory.search("oracle")[0].ticker == "ORCL"
    assert mentioned_symbols("What did Oracle report?", set(), directory) == ["ORCL"]
    assert mentioned_symbols("What was Oracle's last closing price?", set(), directory) == ["ORCL"]
    assert mentioned_symbols("latest RSI", {"NVDA"}, directory) == []


def test_parse_filings_keeps_the_sec_document_link() -> None:
    rows = parse_filings(
        {
            "filings": {
                "recent": {
                    "form": ["4", "4", "4", "10-K", "8-K"],
                    "filingDate": ["2026-10-02", "2026-10-01", "2026-09-30", "2025-11-01", "2026-09-15"],
                    "accessionNumber": [
                        "0000320193-26-000130",
                        "0000320193-26-000123",
                        "0000320193-26-000122",
                        "0000320193-25-000100",
                        "0000320193-26-000090",
                    ],
                    "primaryDocument": ["a.xml", "b.xml", "c.xml", "aapl-10k.htm", "aapl-8k.htm"],
                    "primaryDocDescription": ["", "", "", "Annual report", "Current report"],
                }
            }
        },
        "0000320193",
    )
    forms = [row.form for row in rows]
    assert forms.count("4") == 2
    assert "10-K" in forms
    annual = next(row for row in rows if row.form == "10-K")
    assert annual.url.endswith("/aapl-10k.htm")

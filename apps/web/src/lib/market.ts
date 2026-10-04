import { apiBase } from "@/lib/format";

export type Quote = {
  ticker: string;
  name: string;
  price: string;
  change: string;
  changePercent: string;
  volume: number;
  marketCap: number;
  sector: string;
  industry: string;
  categories: string[];
  asOf: string;
  dataMode: string;
  source?: string;
};

export type Bar = {
  session: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: number;
};

export type Fundamentals = {
  ticker: string;
  revenue: number;
  revenueGrowth: number;
  eps: string;
  epsGrowth: number;
  grossMargin: number;
  operatingMargin: number;
  freeCashFlow: number;
  pe: number | null;
  forwardPe: number | null;
  peg: number | null;
  priceToSales: number | null;
  debtToEquity: number | null;
  roe: number | null;
  roic: number | null;
  nextEarnings: string | null;
  source?: string;
};

export type Technicals = {
  rsi: number | null;
  macd: number | null;
  macdSignal: number | null;
  macdHistogram: number | null;
  sma20: number | null;
  sma50: number | null;
  sma200: number | null;
  ema20: number | null;
  atr: number | null;
  volume: number;
  relativeVolume: number | null;
  support: number | null;
  resistance: number | null;
  methodNote: string;
};

export type Evidence = {
  id: string;
  source: string;
  sourceType: string;
  title: string;
  publishedOn: string;
  author: string | null;
  rating: string | null;
  priceTarget: number | null;
  summary: string;
  url?: string | null;
  synthetic: boolean;
  disclosure: string;
};

export type ResearchBundle = {
  ticker: string;
  items: Evidence[];
  consensus: {
    consensus: string;
    buy: number;
    hold: number;
    sell: number;
    averageTarget: number;
    highTarget: number;
    lowTarget: number;
    upsidePercent: number;
    disclosure: string;
  };
};

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${apiBase()}${path}`, { cache: "no-store" });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export function loadQuotes() {
  return getJson<{ quotes: Quote[]; dataMode?: string }>("/api/v1/market/quotes");
}

export function loadQuote(ticker: string) {
  return getJson<Quote>(`/api/v1/market/quotes/${ticker}`);
}

export function loadHistory(ticker: string) {
  return getJson<{ bars: Bar[] }>(`/api/v1/market/history/${ticker}?limit=180`);
}

export function loadFundamentals(ticker: string) {
  return getJson<Fundamentals>(`/api/v1/market/fundamentals/${ticker}`);
}

export function loadTechnicals(ticker: string) {
  return getJson<Technicals>(`/api/v1/market/technicals/${ticker}`);
}

export function loadResearch(ticker: string) {
  return getJson<ResearchBundle>(`/api/v1/research/${ticker}`);
}

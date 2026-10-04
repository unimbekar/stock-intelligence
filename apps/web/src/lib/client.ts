export type Workspace = {
  user: { email: string; displayName: string; role: string };
  data: { dataMode: string; dataModeLabel: string; source: string; warning: string };
  preference: Preference;
  weights: Record<string, number>;
  portfolio: PortfolioView | null;
  quotes: QuoteRow[];
  indexes: IndexRow[];
  sentiment: { stance: string; score: number; note: string; factors: { name: string; score: number; label: string }[] };
  watchlists: WatchlistRow[];
  mail: { address: string; configured: boolean };
  alerts: AlertRow[];
  journal: JournalRow[];
  savedIdeas: { id: string; ticker: string; title: string; payload: Idea }[];
  asOf: string;
};

export type Preference = {
  capital: string;
  dailyProfitTarget: string;
  tradingStyle: string;
  riskTolerance: string;
  sectors: string[];
  experience: string;
  goals: string;
  onboardingCompleted: boolean;
  maxPositionPct: string;
  maxSectorPct: string;
  maxRiskPerTradePct: string;
  maxDailyLoss: string;
  maxOpenPositions: number;
};

export type PortfolioView = {
  id: string;
  name: string;
  cash: string;
  marketValue: string;
  equity: string;
  buyingPower: string;
  dailyPnl: string;
  dailyReturnPercent: string;
  unrealizedPnl: string;
  realizedPnl: string;
  totalReturnPercent: string;
  requiredReturnPercent: string;
  positions: PositionRow[];
  sectors: { sector: string; weightPercent: string }[];
  transactions: TradeRow[];
  equityCurve: { date: string; equity: string }[];
  performance: {
    winRate: number | null;
    profitFactor: number | null;
    expectancy: string | null;
    maxDrawdown: string | null;
    sharpe: number | null;
    sortino: number | null;
    closedTrades: number;
    note: string;
  };
  risk: {
    openPositions: number;
    maxOpenPositions: number;
    largestPositionPercent: string;
    maxPositionPercent: string;
    largestSector: string | null;
    largestSectorPercent: string | null;
    maxSectorPercent: string;
    dailyLoss: string;
    maxDailyLoss: string;
    dailyLossStatus: string;
    portfolioBeta: string;
    betaNote: string;
    correlations: { left: string; right: string; value: number }[];
    breaches: string[];
  };
};

export type PositionRow = {
  ticker: string;
  name?: string;
  quantity: string;
  averageCost: string;
  price: string;
  marketValue: string;
  weightPercent: string;
  unrealizedPnl: string;
  unrealizedPnlPercent?: string;
  dailyPnl: string;
  realizedPnl: string;
  sector: string;
  eps?: string | null;
  rating?: string;
};

export type TradeRow = {
  id: string;
  ticker: string;
  side: string;
  quantity: string;
  price: string;
  fees: string;
  executedAt: string;
  notes: string;
  strategy: string;
};

export type QuoteRow = {
  ticker: string;
  name: string;
  price: string;
  change: string;
  changePercent: string;
  volume: number;
  marketCap: number;
  sector: string;
};

export type IndexRow = { symbol: string; name: string; value: string; change: string; changePercent: string };

export type WatchlistRow = {
  id: string;
  name: string;
  description: string;
  items: { ticker: string; notes: string; priority: string; targetPrice: string | null; price: string | null; changePercent: string | null }[];
};

export type AlertRow = {
  id: string;
  ticker: string | null;
  alertType: string;
  params: Record<string, string | number | boolean>;
  price: string | null;
  changePercent: string | null;
  email: boolean;
  notified: boolean;
  enabled: boolean;
  triggered: boolean;
  lastTriggeredAt: string | null;
};

export type JournalRow = {
  id: string;
  ticker: string;
  entryThesis: string;
  exitThesis: string;
  strategy: string;
  marketConditions: string;
  emotion: string;
  notes: string;
  screenshotPath: string | null;
  aiReview: { content?: string } | null;
  openedAt: string | null;
  closedAt: string | null;
};

export type Idea = {
  ticker: string;
  company: string;
  price: string;
  score: number;
  confidence: string;
  entryLow: string;
  entryHigh: string;
  stop: string | null;
  target1: string | null;
  target2: string | null;
  riskReward: string | null;
  suggestedShares: string | null;
  suggestedAllocation: string | null;
  bull: string[];
  bear: string[];
  catalyst: string;
  risks: string[];
  evidence: { items: { title: string; summary: string; synthetic: boolean; disclosure: string; source: string }[] };
};

export async function api<T>(path: string, init?: RequestInit): Promise<{ ok: boolean; status: number; body: T | null; detail: string }> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    credentials: "include",
  });
  const text = await response.text();
  const parsed = text ? (JSON.parse(text) as T & { detail?: string }) : null;
  return {
    ok: response.ok,
    status: response.status,
    body: parsed,
    detail: parsed && typeof parsed === "object" && "detail" in parsed ? String(parsed.detail) : "",
  };
}

export function loadWorkspace() {
  return api<Workspace>("/api/v1/workspace");
}

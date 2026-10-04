"use client";

import { PageTitle, SignInPrompt, Stat, useWorkspace } from "@/components/desk";
import { money } from "@/lib/format";

export default function PerformancePage() {
  const { workspace, error } = useWorkspace();
  const portfolio = workspace?.portfolio;
  if (error || !portfolio) {
    return (
      <div className="space-y-4">
        <PageTitle kicker="Performance" title="Performance" />
        {error ? <SignInPrompt /> : <p className="text-sm text-muted">Loading the equity curve.</p>}
      </div>
    );
  }
  const stats = portfolio.performance;
  return (
    <div className="space-y-6">
      <PageTitle kicker="Performance" title="Performance" text={stats.note} />
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Total return" value={`${portfolio.totalReturnPercent}%`} />
        <Stat label="Win rate" value={stats.winRate === null ? "No closed trades" : `${(stats.winRate * 100).toFixed(1)}%`} />
        <Stat label="Profit factor" value={stats.profitFactor === null ? "—" : String(stats.profitFactor)} />
        <Stat label="Expectancy" value={stats.expectancy ? money(stats.expectancy) : "—"} />
        <Stat label="Max drawdown" value={stats.maxDrawdown ? `${stats.maxDrawdown}%` : "—"} />
        <Stat label="Sharpe" value={stats.sharpe === null ? "—" : String(stats.sharpe)} />
        <Stat label="Sortino" value={stats.sortino === null ? "—" : String(stats.sortino)} />
        <Stat label="Closed trades" value={String(stats.closedTrades)} />
      </section>
      <section>
        <h2 className="text-sm font-medium">Equity curve</h2>
        <ul className="mt-2 max-h-80 overflow-auto border border-line text-sm">
          {portfolio.equityCurve.slice(-30).map((point) => (
            <li key={point.date} className="flex justify-between border-t border-line px-3 py-1.5">
              <span className="num">{point.date}</span>
              <span className="num">{money(point.equity)}</span>
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h2 className="text-sm font-medium">Risk</h2>
        <ul className="mt-2 space-y-1 text-sm text-muted">
          <li>
            Largest position {portfolio.risk.largestPositionPercent}% of equity, limit {portfolio.risk.maxPositionPercent}%.
          </li>
          <li>
            {portfolio.risk.largestSector ?? "No sector"} {portfolio.risk.largestSectorPercent ?? "0"}%, limit {portfolio.risk.maxSectorPercent}%.
          </li>
          <li>{portfolio.risk.dailyLossStatus}</li>
          <li>
            Reference beta {portfolio.risk.portfolioBeta}. {portfolio.risk.betaNote}
          </li>
          {portfolio.risk.correlations.map((row) => (
            <li key={`${row.left}-${row.right}`}>
              {row.left} / {row.right}: {row.value}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

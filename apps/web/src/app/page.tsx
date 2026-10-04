"use client";

import Link from "next/link";

import { Notice, PageTitle, SignInPrompt, Stat, tone, useWorkspace } from "@/components/desk";
import { money, signed } from "@/lib/format";

export default function HomePage() {
  const { loading, workspace, error } = useWorkspace();
  const portfolio = workspace?.portfolio;

  return (
    <div className="space-y-8">
      <PageTitle
        kicker="Local workspace"
        title="Meridian"
        text="Paper equity, risk, and research on this machine. A daily profit target is arithmetic, not a forecast."
      />
      {loading ? <p className="text-sm text-muted">Loading the desk.</p> : null}
      {error ? <SignInPrompt /> : null}
      {workspace ? <Notice text={workspace.data.warning} /> : null}
      {portfolio ? (
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Stat label="Equity" value={money(portfolio.equity)} />
          <Stat label="Today's P&L" value={signed(portfolio.dailyPnl)} tone={tone(portfolio.dailyPnl)} />
          <Stat label="Cash" value={money(portfolio.cash)} />
          <Stat label="Required return" value={`${portfolio.requiredReturnPercent}%`} />
        </section>
      ) : null}
      {workspace ? (
        <section className="grid gap-6 lg:grid-cols-2">
          <div>
            <h2 className="text-sm font-medium">Indexes</h2>
            <Tape rows={workspace.indexes} />
          </div>
          <div className="border border-line bg-elevated p-4">
            <h2 className="text-sm font-medium">Sentiment</h2>
            <p className="num mt-2 text-2xl">
              {workspace.sentiment.stance} {workspace.sentiment.score}
            </p>
            <p className="mt-2 text-sm leading-6 text-muted">{workspace.sentiment.note}</p>
          </div>
        </section>
      ) : null}
      {portfolio ? (
        <section className="grid gap-6 lg:grid-cols-2">
          <div>
            <h2 className="text-sm font-medium">Open positions</h2>
            <ul className="mt-3 divide-y divide-line border border-line text-sm">
              {portfolio.positions.map((row) => (
                <li key={row.ticker} className="flex items-center justify-between px-3 py-2">
                  <Link href={`/stocks/${row.ticker}`} className="num">
                    {row.ticker}
                  </Link>
                  <span className={tone(row.dailyPnl)}>{signed(row.dailyPnl)}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h2 className="text-sm font-medium">Risk</h2>
            <ul className="mt-3 space-y-2 text-sm text-muted">
              {portfolio.risk.breaches.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p className="mt-4 text-sm">
              <Link href="/ideas" className="text-accent underline">
                AI ideas
              </Link>
              {" · "}
              <Link href="/desk" className="text-accent underline">
                Trading desk
              </Link>
              {" · "}
              <Link href="/performance" className="text-accent underline">
                Performance
              </Link>
            </p>
          </div>
        </section>
      ) : null}
      {workspace ? (
        <section>
          <h2 className="text-sm font-medium">Recent paper trades</h2>
          <ul className="mt-3 divide-y divide-line border border-line text-sm">
            {workspace.portfolio?.transactions.slice(0, 5).map((row) => (
              <li key={row.id} className="flex justify-between px-3 py-2">
                <span>
                  <span className="num">{row.side}</span> {row.quantity} {row.ticker}
                </span>
                <span className="num">{money(row.price)}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function Tape({ rows }: { rows: { symbol: string; name: string; value: string; changePercent: string }[] }) {
  if (rows.length === 0) return <p className="mt-3 text-sm text-muted">Index levels are unavailable.</p>;
  return (
    <div className="mt-3 overflow-x-auto border border-line">
      <table className="w-full text-left text-sm">
        <tbody>
          {rows.map((row) => (
            <tr key={row.symbol} className="border-t border-line first:border-t-0">
              <td className="px-3 py-2">
                <span className="num">{row.symbol}</span>
                <span className="ml-2 text-muted">{row.name}</span>
              </td>
              <td className="num px-3 py-2">{Number(row.value).toLocaleString("en-US")}</td>
              <td className={`num px-3 py-2 ${tone(row.changePercent)}`}>{signed(row.changePercent)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

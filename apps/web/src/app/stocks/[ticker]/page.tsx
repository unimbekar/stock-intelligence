import Link from "next/link";

import { PriceChart } from "@/components/price-chart";
import { compact, money, signed } from "@/lib/format";
import {
  loadFundamentals,
  loadHistory,
  loadQuote,
  loadResearch,
  loadTechnicals,
} from "@/lib/market";

export default async function StockPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  const symbol = ticker.toUpperCase();
  const quote = await loadQuote(symbol);
  if (!quote) {
    return (
      <section className="max-w-2xl">
        <h1 className="text-3xl font-medium tracking-tight">{symbol}</h1>
        <p className="mt-3 text-sm text-muted">
          No Nasdaq session history was found for that symbol. Return to <Link href="/markets">Markets</Link>.
        </p>
      </section>
    );
  }
  const [history, fundamentals, technicals, research] = await Promise.all([
    loadHistory(symbol),
    loadFundamentals(symbol),
    loadTechnicals(symbol),
    loadResearch(symbol),
  ]);
  const tone = toneFor(quote.change);

  return (
    <div className="space-y-8">
      <header>
        <p className="text-[11px] tracking-[0.18em] text-muted uppercase">
          {quote.categories.join(" · ")}
        </p>
        <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-medium tracking-tight">
              <span className="num">{quote.ticker}</span>
              <span className="ml-3 text-xl text-muted">{quote.name}</span>
            </h1>
            <p className="mt-2 text-sm text-muted">
              {quote.dataMode === "live"
                ? `Last regular session ${quote.asOf}. Not a live quote.`
                : `Close for ${quote.asOf}. Not a live quote.`}
            </p>
          </div>
          <p className="text-right">
            <span className="num block text-3xl">{money(quote.price)}</span>
            <span className={`num text-sm ${tone}`}>
              {signed(quote.change)} ({signed(quote.changePercent)}%)
            </span>
          </p>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Fact label="Market cap" value={compact(quote.marketCap)} />
          <Fact label="Volume" value={compact(quote.volume)} />
          <Fact label="Session" value={quote.asOf} />
          <Fact label="Source" value={quote.source === "nasdaq" ? "Nasdaq EOD" : quote.source ?? "Series"} />
        </div>
      </header>

      <section aria-labelledby="chart-heading">
        <h2 id="chart-heading" className="text-sm font-medium">
          Chart
        </h2>
        <div className="mt-3 border border-line bg-elevated p-2">
          {history && history.bars.length > 0 ? (
            <PriceChart bars={history.bars} />
          ) : (
            <p className="px-3 py-8 text-sm text-muted">Price history is unavailable.</p>
          )}
        </div>
      </section>

      <section aria-labelledby="technical-heading">
        <h2 id="technical-heading" className="text-sm font-medium">
          Technical
        </h2>
        {technicals ? (
          <>
            <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
              <Fact label="RSI" value={formatNum(technicals.rsi)} />
              <Fact label="MACD" value={formatNum(technicals.macd)} />
              <Fact label="Signal" value={formatNum(technicals.macdSignal)} />
              <Fact label="Histogram" value={formatNum(technicals.macdHistogram)} />
              <Fact label="SMA 20" value={formatNum(technicals.sma20)} />
              <Fact label="SMA 50" value={formatNum(technicals.sma50)} />
              <Fact label="SMA 200" value={formatNum(technicals.sma200)} />
              <Fact label="EMA 20" value={formatNum(technicals.ema20)} />
              <Fact label="ATR" value={formatNum(technicals.atr)} />
              <Fact label="Relative volume" value={formatNum(technicals.relativeVolume)} />
              <Fact label="Support" value={formatNum(technicals.support)} />
              <Fact label="Resistance" value={formatNum(technicals.resistance)} />
            </div>
            <p className="mt-3 text-xs leading-5 text-muted">{technicals.methodNote}</p>
          </>
        ) : (
          <p className="mt-3 text-sm text-muted">Technicals are unavailable.</p>
        )}
      </section>

      <section aria-labelledby="fundamental-heading">
        <h2 id="fundamental-heading" className="text-sm font-medium">
          Fundamentals
        </h2>
        {fundamentals ? (
          <>
            <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
              <Fact label="Revenue" value={compact(fundamentals.revenue)} />
              <Fact label="Revenue growth" value={percent(fundamentals.revenueGrowth)} />
              <Fact label="EPS" value={fundamentals.eps} />
              <Fact label="EPS growth" value={percent(fundamentals.epsGrowth)} />
              <Fact label="Gross margin" value={percent(fundamentals.grossMargin)} />
              <Fact label="Operating margin" value={percent(fundamentals.operatingMargin)} />
              <Fact label="Free cash flow" value={compact(fundamentals.freeCashFlow)} />
              <Fact label="P/E" value={formatNum(fundamentals.pe)} />
              <Fact label="Forward P/E" value={formatNum(fundamentals.forwardPe)} />
              <Fact label="PEG" value={formatNum(fundamentals.peg)} />
              <Fact label="Price/Sales" value={formatNum(fundamentals.priceToSales)} />
              <Fact label="Debt/Equity" value={formatNum(fundamentals.debtToEquity)} />
              <Fact label="ROE" value={percent(fundamentals.roe)} />
              <Fact label="ROIC" value={percent(fundamentals.roic)} />
              <Fact label="Next earnings" value={fundamentals.nextEarnings ?? "—"} />
            </div>
            <p className="mt-3 text-xs leading-5 text-muted">
              Source {fundamentals.source ?? "mock"}.
              {fundamentals.source === "sec-edgar"
                ? fundamentals.pe == null
                  ? " Annual figures from SEC EDGAR. P/E is omitted while the price is not a market print."
                  : " Annual figures from SEC EDGAR. P/E is the last session price divided by diluted EPS from that filing."
                : ""}
            </p>
          </>
        ) : (
          <p className="mt-3 text-sm text-muted">Fundamentals are unavailable.</p>
        )}
      </section>

      <section aria-labelledby="research-heading">
        <h2 id="research-heading" className="text-sm font-medium">
          Research evidence
        </h2>
        {research ? (
          <>
            <p className="mt-3 text-sm text-muted">
              {research.consensus.consensus === "Unavailable" ||
              research.consensus.buy + research.consensus.hold + research.consensus.sell === 0
                ? research.consensus.disclosure
                : `Consensus ${research.consensus.consensus}: ${research.consensus.buy} buy, ${research.consensus.hold} hold, ${research.consensus.sell} sell. Average target ${money(research.consensus.averageTarget)} (${signed(research.consensus.upsidePercent)}%). ${research.consensus.disclosure}`}
            </p>
            <div className="mt-4 space-y-3">
              {research.items.map((item) => (
                <article key={item.id} className="border border-line bg-elevated px-4 py-3">
                  <p className="text-xs tracking-[0.14em] text-muted uppercase">
                    {item.source} · {item.sourceType.replace(/_/g, " ")}
                  </p>
                  <h3 className="mt-1 text-sm font-medium">
                    {item.url ? (
                      <a href={item.url} target="_blank" rel="noreferrer">
                        {item.title}
                      </a>
                    ) : (
                      item.title
                    )}
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-muted">{item.summary}</p>
                  <p className="mt-2 text-xs text-muted">{item.disclosure}</p>
                </article>
              ))}
            </div>
          </>
        ) : (
          <p className="mt-3 text-sm text-muted">Research is unavailable.</p>
        )}
      </section>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-line bg-elevated px-3 py-2">
      <p className="text-xs text-muted">{label}</p>
      <p className="num mt-1 text-sm">{value}</p>
    </div>
  );
}

function toneFor(change: string): string {
  const value = Number(change);
  if (value > 0) return "text-positive";
  if (value < 0) return "text-negative";
  return "text-muted";
}

function formatNum(value: number | null): string {
  if (value === null || Number.isNaN(value)) return "—";
  return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

function percent(value: number | null): string {
  if (value === null || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

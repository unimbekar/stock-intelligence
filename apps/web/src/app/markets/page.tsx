import { MarketBoard } from "@/components/market-board";
import { loadQuotes } from "@/lib/market";

export default async function MarketsPage() {
  const payload = await loadQuotes();
  if (!payload) {
    return (
      <section className="max-w-2xl">
        <h1 className="text-3xl font-medium tracking-tight">Markets</h1>
        <p className="mt-3 border border-line bg-elevated px-4 py-3 text-sm text-negative">
          The market tape could not be loaded. Start the API and refresh this page.
        </p>
      </section>
    );
  }
  return <MarketBoard quotes={payload.quotes} live={payload.dataMode === "live"} />;
}

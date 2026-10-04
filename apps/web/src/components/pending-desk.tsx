export function PendingDesk({ title, purpose }: { title: string; purpose: string }) {
  return (
    <section className="max-w-2xl">
      <p className="text-[11px] tracking-[0.18em] text-muted uppercase">In progress</p>
      <h1 className="mt-2 text-3xl font-medium tracking-tight">{title}</h1>
      <p className="mt-3 text-sm leading-6 text-muted">{purpose}</p>
      <p className="mt-4 border border-line bg-elevated px-4 py-3 text-sm leading-6">
        The navigation, demo dataset, and API are in place. This desk gets its working surface in the next
        phase, using the same labeled demo data. Nothing on this page is a live market feed.
      </p>
    </section>
  );
}

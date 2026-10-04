"use client";

import { useEffect, useState } from "react";

type Match = { ticker: string; name: string };

export function SymbolField({
  value,
  onChange,
  placeholder = "Ticker or company",
}: {
  value: string;
  onChange: (ticker: string) => void;
  placeholder?: string;
}) {
  const [query, setQuery] = useState(value);
  const [matches, setMatches] = useState<Match[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setQuery(value);
  }, [value]);

  useEffect(() => {
    const needle = query.trim();
    if (needle.length < 1) {
      setMatches([]);
      return;
    }
    const handle = window.setTimeout(() => {
      fetch(`/api/v1/symbols?q=${encodeURIComponent(needle)}`)
        .then((response) => (response.ok ? response.json() : { matches: [] }))
        .then((body: { matches?: Match[] }) => setMatches(body.matches ?? []))
        .catch(() => setMatches([]));
    }, 180);
    return () => window.clearTimeout(handle);
  }, [query]);

  return (
    <div className="relative">
      <input
        className="w-full border border-line bg-bg px-2 py-1 text-sm"
        value={query}
        placeholder={placeholder}
        onFocus={() => setOpen(true)}
        onChange={(event) => {
          setQuery(event.target.value.toUpperCase());
          setOpen(true);
          onChange(event.target.value.toUpperCase());
        }}
      />
      {open && matches.length > 0 ? (
        <ul className="absolute z-10 mt-1 max-h-56 w-full overflow-auto border border-line bg-elevated text-sm">
          {matches.map((match) => (
            <li key={match.ticker}>
              <button
                type="button"
                className="block w-full px-2 py-1.5 text-left hover:bg-muted-surface"
                onClick={() => {
                  setQuery(match.ticker);
                  onChange(match.ticker);
                  setOpen(false);
                }}
              >
                <span className="num">{match.ticker}</span>
                <span className="ml-2 text-muted">{match.name}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Watchlist } from "@/lib/types";

export function WatchlistSwitcher({
  value,
  onChange,
  watchlists,
}: {
  value: number | null;
  onChange: (id: number) => void;
  watchlists?: Watchlist[];
}) {
  const { data } = useQuery({ queryKey: ["watchlists"], queryFn: api.watchlists });
  const lists = watchlists ?? data ?? [];
  const selectedId = value !== null && lists.some((w) => w.id === value) ? value : lists[0]?.id ?? "";
  return (
    <select
      className="input w-full min-w-[210px] sm:w-[230px]"
      value={selectedId}
      onChange={(e) => onChange(Number(e.target.value))}
      aria-label="Watchlist"
      disabled={lists.length === 0}
    >
      {lists.length === 0 && <option value="">{data === undefined ? "Loading watchlists…" : "No watchlists found"}</option>}
      {lists.map((w) => (
        <option key={w.id} value={w.id}>
          {w.name} ({w.symbols.length})
        </option>
      ))}
    </select>
  );
}

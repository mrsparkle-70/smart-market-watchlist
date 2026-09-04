"use client";

import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { WatchlistSymbol } from "@/lib/types";

export function ReviewControls({ symbols, watchlistId }: { symbols: WatchlistSymbol[]; watchlistId: number }) {
  const qc = useQueryClient();
  const remove = useMutation({
    mutationFn: (symbol: string) => api.removeSymbol(watchlistId, symbol),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["watchlists"] });
      qc.invalidateQueries({ queryKey: ["feed"] });
    },
  });
  const priority = useMutation({
    mutationFn: ({ symbol, value }: { symbol: string; value: string }) => api.updatePriority(watchlistId, symbol, value),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlists"] }),
  });

  return (
    <div className="card">
      <h3 className="mb-3 font-semibold">Watchlist summary</h3>
      {symbols.length === 0 ? (
        <p className="text-sm text-gray-400">No symbols yet — add one to start tracking changes.</p>
      ) : (
        <ul className="divide-y divide-gray-800">
          {symbols.map((s) => (
            <li key={s.symbol} className="flex items-center justify-between gap-2 py-2 text-sm">
              <div className="min-w-0">
                <Link href={`/symbols/${s.symbol}`} className="font-medium hover:underline">
                  {s.symbol}
                </Link>
                <span className="ml-2 text-gray-400">{s.display_name}</span>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <select className="rounded border border-slate-700 bg-slate-950 px-1.5 py-1 text-[11px] text-slate-300" value={s.priority_tag} onChange={(e) => priority.mutate({ symbol: s.symbol, value: e.target.value })} aria-label={`${s.symbol} priority`}>
                  <option value="normal">Normal</option>
                  <option value="high_priority">High priority</option>
                  <option value="long_term">Long term</option>
                  <option value="speculative">Speculative</option>
                  <option value="ignore_short_term">Ignore short term</option>
                </select>
                <button className="text-xs text-gray-500 hover:text-red-400" onClick={() => remove.mutate(s.symbol)}>Remove</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

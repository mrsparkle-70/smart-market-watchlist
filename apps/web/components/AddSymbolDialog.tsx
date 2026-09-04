"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function AddSymbolDialog({ watchlistId }: { watchlistId: number }) {
  const [open, setOpen] = useState(false);
  const [symbol, setSymbol] = useState("");
  const [error, setError] = useState("");
  const qc = useQueryClient();
  const suggestions = useQuery({
    queryKey: ["symbol-search", symbol],
    queryFn: () => api.searchSymbols(symbol),
    enabled: open && symbol.length >= 2,
    staleTime: 30_000,
  });
  const add = useMutation({
    mutationFn: (s: string) => api.addSymbol(watchlistId, s),
    onSuccess: () => {
      setSymbol("");
      setError("");
      setOpen(false);
      qc.invalidateQueries({ queryKey: ["watchlists"] });
      qc.invalidateQueries({ queryKey: ["feed"] });
    },
    onError: (e: Error) => setError(e.message),
  });

  if (!open) return <button className="btn-ghost" onClick={() => setOpen(true)}>+ Add symbol</button>;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setOpen(false)}>
      <div className="card mx-4 w-[calc(100%-2rem)] max-w-md" onClick={(e) => e.stopPropagation()}>
        <h3 className="mb-3 text-lg font-semibold">Add symbol</h3>
        <input
          className="input uppercase"
          placeholder="e.g. NVDA"
          value={symbol}
          autoFocus
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          onKeyDown={(e) => e.key === "Enter" && symbol && add.mutate(symbol)}
        />
        {suggestions.data && suggestions.data.length > 0 && (
          <div className="mt-2 max-h-48 overflow-y-auto rounded-lg border b-line bg-slate-950/80 p-1">
            {suggestions.data.map((match) => (
              <button key={`${match.symbol}-${match.exchange}`} type="button" className="flex w-full items-center justify-between rounded-md px-2 py-2 text-left text-sm hover:bg-rose-400/10" onClick={() => setSymbol(match.symbol)}>
                <span className="font-num font-semibold">{match.symbol}</span>
                <span className="ml-3 truncate text-xs text-slate-500">{match.name || match.exchange}</span>
              </button>
            ))}
          </div>
        )}
        {suggestions.isFetching && <p className="mt-2 text-xs text-slate-500">Searching symbols…</p>}
        {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <button className="btn-ghost" onClick={() => setOpen(false)}>Cancel</button>
          <button className="btn" disabled={!symbol || add.isPending} onClick={() => add.mutate(symbol)}>
            Add
          </button>
        </div>
      </div>
    </div>
  );
}

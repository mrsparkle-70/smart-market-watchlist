"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export default function WatchlistsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [editing, setEditing] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [bulkTarget, setBulkTarget] = useState<number | null>(null);
  const [bulkText, setBulkText] = useState("");
  const lists = useQuery({ queryKey: ["watchlists"], queryFn: api.watchlists });
  const create = useMutation({
    mutationFn: () => api.createWatchlist(name),
    onSuccess: () => { setName(""); qc.invalidateQueries({ queryKey: ["watchlists"] }); },
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.deleteWatchlist(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlists"] }),
    onError: (e: Error) => alert(e.message),
  });
  const rename = useMutation({
    mutationFn: () => api.renameWatchlist(editing as number, editName),
    onSuccess: () => { setEditing(null); setEditName(""); qc.invalidateQueries({ queryKey: ["watchlists"] }); },
  });
  const bulkAdd = useMutation({
    mutationFn: () => api.bulkAddSymbols(bulkTarget as number, [bulkText]),
    onSuccess: () => { setBulkText(""); setBulkTarget(null); qc.invalidateQueries({ queryKey: ["watchlists"] }); },
  });
  const reorder = useMutation({
    mutationFn: ({ id, symbols }: { id: number; symbols: string[] }) => api.reorderSymbols(id, symbols),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlists"] }),
  });

  function moveSymbol(id: number, symbols: string[], index: number, direction: -1 | 1) {
    const next = [...symbols];
    const target = index + direction;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    reorder.mutate({ id, symbols: next });
  }

  return (
    <main className="mx-auto max-w-3xl space-y-4 p-6">
      <a href="/dashboard" className="text-sm text-gray-400 hover:text-gray-200">← Back to dashboard</a>
      <h1 className="text-2xl font-bold">Watchlists</h1>
      <div className="flex gap-2">
        <input className="input" placeholder="New watchlist name" value={name}
               onChange={(e) => setName(e.target.value)} />
        <button className="btn shrink-0" disabled={!name || create.isPending} onClick={() => create.mutate()}>Create</button>
      </div>
      {bulkTarget && (
        <div className="panel space-y-3 border-rose-400/30 p-4">
          <div className="flex items-center justify-between gap-2">
            <div><h2 className="font-semibold">Import symbols in bulk</h2><p className="text-xs text-slate-500">Paste tickers separated by spaces, commas, or new lines. Up to 100.</p></div>
            <button className="btn-ghost" onClick={() => setBulkTarget(null)}>Close</button>
          </div>
          <textarea className="input min-h-24" placeholder="AAPL, NVDA, MSFT\nTSLA" value={bulkText} onChange={(e) => setBulkText(e.target.value)} />
          <button className="btn" disabled={!bulkText.trim() || bulkAdd.isPending} onClick={() => bulkAdd.mutate()}>{bulkAdd.isPending ? "Importing…" : "Import symbols"}</button>
          {bulkAdd.data && <p className="text-xs text-emerald-300">Added {bulkAdd.data.added.length}; skipped {bulkAdd.data.errors.length}.</p>}
          {bulkAdd.error && <p className="text-xs text-rose-300">{(bulkAdd.error as Error).message}</p>}
        </div>
      )}
      <ul className="space-y-2">
        {lists.data?.map((w) => (
          <li key={w.id} className="card flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            {editing === w.id ? (
              <div className="flex min-w-0 flex-1 gap-2">
                <input className="input" value={editName} onChange={(e) => setEditName(e.target.value)} autoFocus />
                <button className="btn shrink-0" disabled={!editName.trim() || rename.isPending} onClick={() => rename.mutate()}>Save</button>
                <button className="btn-ghost shrink-0" onClick={() => setEditing(null)}>Cancel</button>
              </div>
            ) : (
              <div className="min-w-0">
                <span className="font-medium">{w.name}</span>
                {w.is_default && <span className="ml-2 text-xs text-gray-500">default</span>}
                <span className="ml-2 text-sm text-gray-400">{w.symbols.length} symbols</span>
                {w.symbols.length > 0 && <div className="mt-3 flex flex-wrap gap-1.5">
                  {w.symbols.map((s, index) => <span key={s.symbol} className="inline-flex items-center gap-1 rounded-md border b-line bg-slate-950/40 px-2 py-1 text-xs text-slate-300">
                    <span className="font-num">{s.symbol}</span>
                    <button className="text-slate-500 hover:text-rose-300" disabled={index === 0 || reorder.isPending} onClick={() => moveSymbol(w.id, w.symbols.map((item) => item.symbol), index, -1)} aria-label={`Move ${s.symbol} up`}>↑</button>
                    <button className="text-slate-500 hover:text-rose-300" disabled={index === w.symbols.length - 1 || reorder.isPending} onClick={() => moveSymbol(w.id, w.symbols.map((item) => item.symbol), index, 1)} aria-label={`Move ${s.symbol} down`}>↓</button>
                  </span>)}
                </div>}
              </div>
            )}
            {editing !== w.id && <div className="flex shrink-0 gap-3">
              <button className="text-xs text-slate-400 hover:text-rose-300" onClick={() => setBulkTarget(w.id)}>Import</button>
              <button className="text-xs text-slate-400 hover:text-rose-300" onClick={() => { setEditing(w.id); setEditName(w.name); }}>Rename</button>
              {!w.is_default && <button className="text-xs text-gray-500 hover:text-red-400" onClick={() => remove.mutate(w.id)}>Delete</button>}
            </div>}
          </li>
        ))}
      </ul>
    </main>
  );
}

"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

const money = (value: number | null) => value === null ? "—" : `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function PortfolioPanel() {
  const qc = useQueryClient();
  const [symbol, setSymbol] = useState("");
  const [quantity, setQuantity] = useState("");
  const [cost, setCost] = useState("");
  const portfolio = useQuery({ queryKey: ["portfolio"], queryFn: api.portfolio });
  const save = useMutation({
    mutationFn: () => api.saveHolding(symbol.toUpperCase(), Number(quantity), Number(cost)),
    onSuccess: () => { setSymbol(""); setQuantity(""); setCost(""); qc.invalidateQueries({ queryKey: ["portfolio"] }); },
  });
  const remove = useMutation({
    mutationFn: (ticker: string) => api.deleteHolding(ticker),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio"] }),
  });
  const summary = portfolio.data;
  const gain = summary?.unrealized_gain ?? 0;
  return (
    <section className="panel overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b b-line px-4 py-3">
        <div><div className="kpi-label">Portfolio view</div><h2 className="mt-0.5 font-semibold">Position tracker</h2></div>
        <div className="text-right"><div className="font-num font-semibold">{money(summary?.market_value ?? null)}</div><div className={`font-num text-xs ${gain >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{gain >= 0 ? "+" : ""}{money(gain)} unrealized</div></div>
      </div>
      <div className="grid gap-3 border-b b-line p-3 sm:grid-cols-2">
        <input className="input" placeholder="Symbol" value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} />
        <input className="input min-w-0" type="number" min="0.0001" step="any" placeholder="Quantity" aria-label="Quantity" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
        <input className="input min-w-0" type="number" min="0.01" step="0.01" placeholder="Avg cost" aria-label="Average cost" value={cost} onChange={(e) => setCost(e.target.value)} />
        <button className="btn w-full sm:col-span-2" disabled={!symbol || Number(quantity) <= 0 || Number(cost) <= 0 || save.isPending} onClick={() => save.mutate()}>{save.isPending ? "Saving…" : "Save position"}</button>
      </div>
      {save.error && <p className="px-4 pt-2 text-xs text-rose-300">{(save.error as Error).message}</p>}
      {summary?.items.length ? <div className="divide-y divide-slate-800/70">
        {summary.items.map((item) => <div key={item.symbol} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
          <div><span className="font-num font-semibold">{item.symbol}</span><span className="ml-2 text-xs text-slate-500">{item.quantity} shares · cost {money(item.invested_value)}</span></div>
          <div className="flex items-center gap-3 text-right"><div><div className="font-num font-semibold">{money(item.market_value)}</div><div className={`font-num text-xs ${(item.unrealized_gain ?? 0) >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{item.unrealized_gain === null ? "Unpriced" : `${item.unrealized_gain >= 0 ? "+" : ""}${money(item.unrealized_gain)}`}</div></div><button className="text-xs text-slate-500 hover:text-rose-300" onClick={() => remove.mutate(item.symbol)}>Remove</button></div>
        </div>)}
      </div> : <p className="px-4 py-4 text-sm text-slate-500">Add a position to track value and unrealized performance. This does not place trades.</p>}
      {summary && summary.items.length > 0 && summary.priced_items < summary.items.length && <p className="border-t b-line px-4 py-2 text-[11px] text-amber-300">{summary.items.length - summary.priced_items} position(s) have no provider snapshot yet.</p>}
    </section>
  );
}

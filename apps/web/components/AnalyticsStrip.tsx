"use client";

import type { SymbolAnalytics } from "@/lib/types";

export function AnalyticsStrip({ data }: { data: SymbolAnalytics }) {
  const pct = data.return_pct;
  const tone = (pct ?? 0) >= 0 ? "text-emerald-400" : "text-rose-400";
  const money = (value: number | null) => value === null ? "—" : `$${value.toFixed(2)}`;
  const cards = [
    ["Window return", pct === null ? "—" : `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`, tone],
    ["Observed high", money(data.high), "text-slate-100"],
    ["Observed low", money(data.low), "text-slate-100"],
    ["Max drawdown", data.max_drawdown_pct === null ? "—" : `${data.max_drawdown_pct.toFixed(2)}%`, "text-rose-300"],
  ];
  return <section className="grid grid-cols-2 gap-2 sm:grid-cols-4">
    {cards.map(([label, value, className]) => <div key={label} className="panel p-3"><div className="kpi-label">{label}</div><div className={`font-num mt-1 text-lg font-semibold ${className}`}>{value}</div></div>)}
  </section>;
}

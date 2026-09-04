"use client";

import type { Quote } from "@/lib/types";

export function SymbolMetricGrid({ quote }: { quote?: Quote }) {
  const metrics = [["Previous close", quote ? `$${quote.previous_close.toFixed(2)}` : "—"], ["Open", quote?.open_price == null ? "—" : `$${quote.open_price.toFixed(2)}`], ["Day high", quote?.high_price == null ? "—" : `$${quote.high_price.toFixed(2)}`], ["Day low", quote?.low_price == null ? "—" : `$${quote.low_price.toFixed(2)}`], ["Volume", quote?.volume == null ? "—" : quote.volume.toLocaleString()], ["Data quality", quote?.data_quality ?? "—"]];
  return <section className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6" aria-label="Market metrics">{metrics.map(([label, value]) => <div key={label} className="panel panel-hover min-w-0 p-3.5"><div className="kpi-label truncate">{label}</div><div className="mt-2 truncate font-num text-base font-semibold text-slate-100">{value}</div></div>)}</section>;
}

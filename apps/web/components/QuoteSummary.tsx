"use client";

import type { Quote } from "@/lib/types";
import { DataFreshnessBadge } from "./DataFreshnessBadge";

export function QuoteSummary({ quote }: { quote: Quote }) {
  const up = (quote.change_since_close_pct ?? 0) >= 0;
  return (
    <div className="card flex flex-col items-start justify-between gap-4 sm:flex-row">
      <div>
        <div className="flex items-center gap-2">
          <h2 className="text-2xl font-bold">{quote.symbol}</h2>
          <DataFreshnessBadge freshness={quote.freshness} marketStatus={quote.market_status} />
        </div>
        <div className="mt-1 flex items-baseline gap-3">
          <span className="text-3xl font-semibold">${quote.price.toFixed(2)}</span>
          <span className={`text-lg ${up ? "text-emerald-400" : "text-red-400"}`}>
            {up ? "+" : ""}{quote.change_since_close_pct?.toFixed(2)}%
          </span>
        </div>
        <p className="mt-1 text-xs text-gray-500">
          Prev close ${quote.previous_close.toFixed(2)} · market {quote.market_status} · provider {quote.provider}
          {quote.source_timestamp && ` · as of ${new Date(quote.source_timestamp).toLocaleTimeString()}`}
        </p>
      </div>
      <div className="grid w-full grid-cols-2 gap-x-6 gap-y-1 text-left text-sm text-gray-400 sm:w-auto sm:grid-cols-1 sm:text-right">
        <p>Open ${quote.open_price?.toFixed(2) ?? "—"}</p>
        <p>High ${quote.high_price?.toFixed(2) ?? "—"}</p>
        <p>Low ${quote.low_price?.toFixed(2) ?? "—"}</p>
        <p>Vol {quote.volume ? quote.volume.toLocaleString() : "—"}</p>
      </div>
    </div>
  );
}

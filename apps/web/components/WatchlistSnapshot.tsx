"use client";

import Link from "next/link";
import { useQueries } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { WatchlistSymbol } from "@/lib/types";
import { DataFreshnessBadge } from "./DataFreshnessBadge";

export function WatchlistSnapshot({ symbols }: { symbols: WatchlistSymbol[] }) {
  const quotes = useQueries({
    queries: symbols.map((item) => ({
      queryKey: ["latest", item.symbol],
      queryFn: () => api.latest(item.symbol),
      staleTime: 60_000,
    })),
  });

  return (
    <section className="panel overflow-hidden">
      <div className="flex items-center justify-between border-b b-line px-4 py-3">
        <div>
          <div className="kpi-label">Your watchlist</div>
          <h2 className="mt-0.5 font-semibold">Latest market snapshot</h2>
        </div>
        <span className="text-xs text-slate-500">{symbols.length} symbols</span>
      </div>
      <div className="divide-y divide-slate-800/70">
        {symbols.map((item, index) => {
          const result = quotes[index];
          const quote = result.data;
          const move = quote?.change_since_close_pct ?? 0;
          return (
            <div key={item.symbol} className="flex items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0">
                <Link href={`/symbols/${item.symbol}`} className="font-num font-semibold hover:text-rose-300 hover:underline">
                  {item.symbol}
                </Link>
                <p className="truncate text-xs text-slate-500">{item.display_name}</p>
              </div>
              {result.isLoading ? (
                <div className="skeleton h-8 w-24" />
              ) : result.isError ? (
                <span className="text-right text-xs text-rose-300">Data unavailable</span>
              ) : quote ? (
                <div className="text-right">
                  <div className="font-num font-semibold">${quote.price.toFixed(2)}</div>
                  <div className="flex items-center justify-end gap-2">
                    <span className={`font-num text-xs font-semibold ${move >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                      {move >= 0 ? "+" : ""}{move.toFixed(2)}%
                    </span>
                    <DataFreshnessBadge freshness={quote.freshness} marketStatus={quote.market_status} />
                  </div>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}

"use client";

import type { NewsItem } from "@/lib/types";
import { SymbolEmpty, SymbolError, SymbolSkeleton } from "./SymbolState";

export function SymbolNewsList({ news, loading, error, onRetry }: { news?: NewsItem[]; loading: boolean; error?: unknown; onRetry: () => void }) {
  if (loading) return <div className="space-y-2"><SymbolSkeleton className="h-16" /><SymbolSkeleton className="h-16" /><SymbolSkeleton className="h-16" /></div>;
  if (error) return <SymbolError title="News unavailable" error={error} onRetry={onRetry} />;
  if (!news?.length) return <SymbolEmpty title="No scored news yet" detail="Provider news will appear here when there is a relevant story for this symbol." />;
  return <ul className="space-y-2">{news.slice(0, 6).map((item, index) => { const sentiment = item.sentiment_label.toLowerCase(); const tone = sentiment === "positive" ? "text-emerald-300" : sentiment === "negative" ? "text-rose-300" : "text-slate-400"; return <li key={`${item.url}-${index}`} className="group rounded-xl border b-line bg-slate-950/25 p-3 transition hover:border-rose-300/25 hover:bg-rose-400/[0.04]"><div className="flex items-start justify-between gap-3"><a href={item.url} target="_blank" rel="noreferrer" className="text-sm font-medium leading-snug text-slate-200 group-hover:text-white">{item.headline}</a><span className={`shrink-0 text-[10px] font-semibold uppercase tracking-wider ${tone}`}>{item.sentiment_label}</span></div><div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500"><span>{item.source}{item.published_at ? ` · ${new Date(item.published_at).toLocaleDateString()}` : ""}</span><span className="font-num">relevance {item.relevance_score.toFixed(0)}/100</span></div></li>; })}</ul>;
}

"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AttentionCard as Card } from "@/lib/types";
import { DataFreshnessBadge } from "./DataFreshnessBadge";

// Event-type identity: label + icon + accent color (drives the design language)
export const EVENT_META: Record<string, { label: string; icon: string; color: string }> = {
  earnings: { label: "Earnings", icon: "💰", color: "#34d399" },
  earnings_surprise: { label: "Earnings surprise", icon: "🎯", color: "#34d399" },
  guidance_change: { label: "Guidance", icon: "🧭", color: "#fbbf24" },
  dividend_change: { label: "Dividend", icon: "🪙", color: "#34d399" },
  stock_split: { label: "Stock split", icon: "✂️", color: "#60a5fa" },
  analyst_change: { label: "Analyst action", icon: "📊", color: "#60a5fa" },
  merger_acquisition: { label: "M&A", icon: "🤝", color: "#c084fc" },
  news_impact: { label: "News", icon: "📰", color: "#38bdf8" },
  price_move: { label: "Price move", icon: "📈", color: "#fbbf24" },
  unusual_volume: { label: "Unusual volume", icon: "🔊", color: "#a78bfa" },
  volatility_spike: { label: "Volatility", icon: "🌊", color: "#fb7185" },
  ma_break: { label: "Trend break", icon: "📉", color: "#f472b6" },
  gap: { label: "Gap", icon: "🕳️", color: "#fb923c" },
  relative_move: { label: "Relative move", icon: "⚖️", color: "#22d3ee" },
  personal_threshold: { label: "Personal watch", icon: "⭐", color: "#34d399" },
};

const SEVERITY_BADGE: Record<string, { label: string; cls: string }> = {
  investigate: { label: "Investigate now", cls: "bg-rose-500/15 text-rose-300 border-rose-400/40" },
  review: { label: "Worth reviewing", cls: "bg-amber-500/15 text-amber-300 border-amber-400/40" },
  notable: { label: "Notable", cls: "bg-rose-500/15 text-rose-300 border-rose-400/40" },
  background: { label: "Background", cls: "bg-slate-600/20 text-slate-400 border-slate-500/40" },
};

function fmtPct(v: number | null | undefined) {
  if (v === null || v === undefined) return "—";
  return `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
}

export function AttentionCard({ card }: { card: Card }) {
  const qc = useQueryClient();
  const state = useMutation({
    mutationFn: (action: "reviewed" | "dismiss" | "save") => api.eventState(card.id, action),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["feed"] }),
  });

  const meta = EVENT_META[card.event_type] ?? { label: card.event_type, icon: "🔸", color: "#94a3b8" };
  const sev = SEVERITY_BADGE[card.severity] ?? SEVERITY_BADGE.background;
  const related = card.evidence?.extra?.related_events ?? [];
  const up = (card.change_since_close_pct ?? 0) >= 0;
  const score = Math.round(card.final_score);

  return (
    <div className={`feed-card feed-sv-${card.severity} p-5`}>
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row">
        {/* Identity */}
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-base"
              style={{ backgroundColor: `${meta.color}1a`, color: meta.color }}
            >
              {meta.icon}
            </span>
            <a href={`/symbols/${card.symbol}`} className="group inline-flex min-w-0 items-center gap-2">
              <span className="font-num text-xl font-bold tracking-tight group-hover:underline">{card.symbol}</span>
              <span className="max-w-[14rem] truncate text-sm text-slate-400">{card.company_name}</span>
            </a>
            <span className="chip" style={{ borderColor: `${meta.color}55`, color: meta.color }}>{meta.label}</span>
            <DataFreshnessBadge freshness={card.freshness} />
          </div>
          <p className="mt-2 text-sm text-slate-300">{card.title}</p>
        </div>

        {/* Price + move */}
        <div className="w-full shrink-0 text-left sm:w-auto sm:text-right">
          <div className="font-num text-2xl font-bold">
            {card.price !== null ? `$${card.price.toFixed(2)}` : "—"}
          </div>
          <div className="font-num text-sm font-semibold" style={{ color: up ? "var(--up)" : "var(--down)" }}>
            {fmtPct(card.change_since_close_pct)} today
          </div>
          {card.change_since_last_visit_pct !== null && (
            <div className="font-num text-xs text-slate-400">
              {fmtPct(card.change_since_last_visit_pct)} since last visit
            </div>
          )}
        </div>
      </div>

      <p className="summary-copy mt-3 text-sm leading-relaxed text-slate-300">{card.summary}</p>

      {/* Grouped signals (noise control) */}
      {related.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] uppercase tracking-wide text-slate-500">Signals:</span>
          {related.slice(0, 4).map((r, i) => {
            const rm = EVENT_META[r.type];
            return (
              <span key={i} className="chip chip-off font-num">
                {rm?.icon ?? ""} {r.type.replace(/_/g, " ")}
              </span>
            );
          })}
        </div>
      )}

      {/* Score + confidence + severity */}
      <div className="mt-4 flex flex-wrap items-center gap-4">
        <div className="min-w-40 flex-1">
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="kpi-label">Attention</span>
            <span className="font-num font-semibold text-slate-200">{score}/100</span>
          </div>
          <div className="score-bar"><div style={{ width: `${score}%` }} /></div>
        </div>
        <div className="text-center">
          <div className="font-num text-sm font-semibold text-slate-300">
            {(card.confidence_score * 100).toFixed(0)}%
          </div>
          <div className="kpi-label">confidence</div>
        </div>
        <span className={`chip ${sev.cls}`}>{sev.label}</span>
      </div>

      {/* Actions */}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t b-line pt-3">
        <span className="font-num text-xs text-slate-500">
          {new Date(card.detected_at).toLocaleString()} · {card.evidence?.source}
        </span>
        <div className="flex gap-2">
          {!card.user_state.reviewed_at && (
            <button className="btn" onClick={() => state.mutate("reviewed")} disabled={state.isPending}>
              ✓ Mark reviewed
            </button>
          )}
          <button className="btn-ghost" onClick={() => state.mutate("dismiss")} disabled={state.isPending}>
            Dismiss
          </button>
          <button className="btn-ghost" onClick={() => state.mutate("save")} disabled={state.isPending}>
            Save
          </button>
        </div>
      </div>

      {/* Explainability */}
      {card.evidence && (
        <details className="details-block mt-3 rounded-xl bg-slate-950/40 px-4 py-3 text-xs text-slate-400">
          <summary className="cursor-pointer select-none font-medium text-slate-300 hover:text-slate-100">
            ⚙ Why this score? <span className="text-slate-500">(evidence)</span>
          </summary>
          <dl className="mt-3 grid gap-x-6 gap-y-2 sm:grid-cols-2">
            {[
              ["Trigger", card.evidence.trigger],
              ["Baseline", card.evidence.baseline],
              ["Current value", card.evidence.current],
              ["Window", card.evidence.window],
              ["Data source", card.evidence.source],
              ["Confidence", `${(card.evidence.confidence * 100).toFixed(0)}%`],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="kpi-label">{k}</dt>
                <dd className="mt-0.5 break-words text-slate-300">{v || "—"}</dd>
              </div>
            ))}
          </dl>
        </details>
      )}
    </div>
  );
}

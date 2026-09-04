import type { AttentionFeed, Watchlist } from "@/lib/types";

export function DashboardPulse({ feed, watchlist, loading = false, error = false }: { feed?: AttentionFeed; watchlist?: Watchlist; loading?: boolean; error?: boolean }) {
  const summary = feed?.summary;
  const positive = summary?.biggest_positive_move;
  const negative = summary?.biggest_negative_move;
  return (
    <section className="grid gap-4 2xl:grid-cols-[minmax(0,1.45fr)_minmax(360px,0.75fr)]">
      <div className="relative overflow-hidden rounded-3xl border border-rose-300/20 bg-[radial-gradient(circle_at_90%_0%,rgba(244,63,94,0.22),transparent_40%),linear-gradient(135deg,rgba(21,14,24,0.98),rgba(13,19,32,0.94))] p-5 sm:p-7">
        <div className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full border border-rose-300/10" />
        <div className="pointer-events-none absolute -right-8 -top-12 h-40 w-40 rounded-full border border-orange-300/10" />
        <div className="relative">
          <div className="flex flex-wrap items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-rose-300/80"><span className="h-1.5 w-1.5 rounded-full bg-rose-400 shadow-[0_0_12px_rgba(251,113,133,0.9)]" /> Change intelligence</div>
          <h1 className="mt-4 max-w-2xl text-2xl font-semibold tracking-tight text-slate-50 sm:text-3xl">{error ? "Market brief unavailable" : loading ? "Reading your market…" : feed?.change_brief ?? "Your market brief is ready"}</h1>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-slate-400">A focused view of what moved, what is stale, and what deserves a second look since your last visit.</p>
          <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-3 text-xs text-slate-500">
            <span><strong className="font-num text-lg text-slate-200">{watchlist?.symbols.length ?? "—"}</strong> tracked symbols</span>
            <span><strong className="font-num text-lg text-rose-300">{summary?.meaningful_changes ?? "—"}</strong> meaningful changes</span>
            <span><strong className="font-num text-lg text-amber-300">{summary?.stale_instruments ?? "—"}</strong> stale</span>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 2xl:grid-cols-2">
        <Metric label="Market pulse" value={positive ? `+${positive.change_pct.toFixed(1)}%` : "—"} detail={positive ? `${positive.symbol} leading` : "No move yet"} tone="up" />
        <Metric label="Watch closely" value={negative ? `${negative.change_pct.toFixed(1)}%` : "—"} detail={negative ? `${negative.symbol} lagging` : "No move yet"} tone="down" />
        <Metric label="Since last check" value={feed?.since ? new Date(feed.since).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "First visit"} detail={feed?.since ? "comparison window" : "baseline will build"} />
        <Metric label="Attention queue" value={summary ? String(summary.meaningful_changes) : "—"} detail="ranked signals" tone={summary?.meaningful_changes ? "accent" : undefined} />
      </div>
    </section>
  );
}

function Metric({ label, value, detail, tone }: { label: string; value: string; detail: string; tone?: "up" | "down" | "accent" }) {
  const valueClass = tone === "up" ? "text-emerald-300" : tone === "down" ? "text-rose-300" : tone === "accent" ? "text-orange-300" : "text-slate-100";
  return <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4"><p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-600">{label}</p><p className={`font-num mt-3 truncate text-xl font-semibold ${valueClass}`}>{value}</p><p className="mt-1 truncate text-[11px] text-slate-500">{detail}</p></div>;
}

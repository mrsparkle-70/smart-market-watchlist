"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AttentionFeed } from "@/components/AttentionFeed";
import { WatchlistSwitcher } from "@/components/WatchlistSwitcher";
import { AddSymbolDialog } from "@/components/AddSymbolDialog";
import { ReviewControls } from "@/components/ReviewControls";
import { WatchlistSnapshot } from "@/components/WatchlistSnapshot";
import { PortfolioPanel } from "@/components/PortfolioPanel";
import { EVENT_META } from "@/components/AttentionCard";
import { DashboardPulse } from "@/components/dashboard/DashboardPulse";
import { DashboardSectionHeader } from "@/components/dashboard/DashboardSectionHeader";
import { DashboardShell } from "@/components/dashboard/DashboardShell";

export default function DashboardPage() {
  const qc = useQueryClient();
  const [watchlistId, setWatchlistId] = useState<number | null>(null);
  const [scenario, setScenario] = useState("earnings_beat");
  const [visitRecorded, setVisitRecorded] = useState(false);
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<"attention" | "recent" | "move">("attention");
  const [savedOnly, setSavedOnly] = useState(false);
  const [hideReviewed, setHideReviewed] = useState(false);
  const [compact, setCompact] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);
  const refreshedWatchlists = useRef(new Set<number>());

  // Preserve the user's last selected watchlist (section 13)
  useEffect(() => {
    const saved = localStorage.getItem("smw_watchlist_id");
    if (saved) setWatchlistId(Number(saved));
  }, []);
  useEffect(() => {
    if (watchlistId) localStorage.setItem("smw_watchlist_id", String(watchlistId));
  }, [watchlistId]);
  useEffect(() => {
    setCompact(localStorage.getItem("smw_compact") === "1");
    setAutoRefresh(localStorage.getItem("smw_auto_refresh") === "1");
  }, []);
  useEffect(() => {
    localStorage.setItem("smw_compact", compact ? "1" : "0");
  }, [compact]);
  useEffect(() => {
    localStorage.setItem("smw_auto_refresh", autoRefresh ? "1" : "0");
  }, [autoRefresh]);
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "/" && document.activeElement?.tagName !== "INPUT") {
        event.preventDefault();
        document.getElementById("feed-search")?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const watchlists = useQuery({ queryKey: ["watchlists"], queryFn: api.watchlists });
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, staleTime: 60_000 });
  const scenarios = useQuery({ queryKey: ["scenarios"], queryFn: api.scenarios });
  const feed = useQuery({
    queryKey: ["feed", watchlistId],
    queryFn: () => api.feed(watchlistId ?? undefined),
  });

  const refresh = useMutation({
    mutationFn: (id: number) => api.refreshWatchlist(id),
    onSuccess: () => {
      setLastRefresh(new Date().toISOString());
      qc.invalidateQueries({ queryKey: ["feed"] });
      qc.invalidateQueries({ queryKey: ["watchlists"] });
    },
  });

  // Record the visit ONLY after the page loaded successfully (section 7)
  useEffect(() => {
    if (feed.isSuccess && !visitRecorded) {
      api.visit().finally(() => setVisitRecorded(true));
    }
  }, [feed.isSuccess, visitRecorded]);

  const demo = useMutation({
    mutationFn: () => api.demoSimulate(scenario),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["feed"] });
      qc.invalidateQueries({ queryKey: ["watchlists"] });
    },
  });

  const wl = watchlists.data?.find((w) => w.id === (watchlistId ?? watchlists.data?.[0]?.id));
  const s = feed.data?.summary;
  const cards = feed.data?.cards ?? [];
  const shown = cards
    .filter((c) => !typeFilter || c.event_type === typeFilter)
    .filter((c) => !savedOnly || Boolean(c.user_state.saved_at))
    .filter((c) => !hideReviewed || !c.user_state.reviewed_at)
    .filter((c) => {
      const needle = search.trim().toLowerCase();
      return !needle || `${c.symbol} ${c.company_name} ${c.title} ${c.summary}`.toLowerCase().includes(needle);
    })
    .sort((a, b) => sortBy === "recent"
      ? new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime()
      : sortBy === "move"
        ? Math.abs(b.change_since_close_pct ?? 0) - Math.abs(a.change_since_close_pct ?? 0)
        : b.final_score - a.final_score);
  const presentTypes = Array.from(new Set(cards.map((c) => c.event_type))).slice(0, 6);
  const demoEnabled = health.data?.provider === "mock";

  // Build the first market snapshot automatically so a newly-added watchlist
  // has prices immediately. Subsequent refreshes remain user-controlled.
  useEffect(() => {
    if (wl && wl.symbols.length > 0 && !refreshedWatchlists.current.has(wl.id)) {
      refreshedWatchlists.current.add(wl.id);
      refresh.mutate(wl.id);
    }
  }, [wl?.id, wl?.symbols.length]);
  useEffect(() => {
    if (!autoRefresh || !wl || wl.symbols.length === 0) return;
    const timer = window.setInterval(() => {
      if (!refresh.isPending) refresh.mutate(wl.id);
    }, 5 * 60 * 1000);
    return () => window.clearInterval(timer);
  }, [autoRefresh, wl?.id, wl?.symbols.length, refresh.isPending]);

  function exportCsv() {
    const rows = [
      ["Symbol", "Company", "Event", "Severity", "Attention", "Price", "Move today", "Detected"],
      ...shown.map((c) => [c.symbol, c.company_name, c.title, c.severity, String(Math.round(c.final_score)),
        c.price === null ? "" : c.price.toFixed(2), c.change_since_close_pct === null ? "" : `${c.change_since_close_pct.toFixed(2)}%`, c.detected_at]),
    ];
    const csv = rows.map((row) => row.map((value) => `"${value.replaceAll('"', '""')}"`).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `market-watchlist-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <DashboardShell
      watchlistName={wl?.name}
      symbolCount={wl?.symbols.length ?? 0}
      provider={health.data?.provider}
      actions={
        <>
          <WatchlistSwitcher value={watchlistId ?? watchlists.data?.[0]?.id ?? null} onChange={setWatchlistId} watchlists={watchlists.data} />
          {wl && wl.symbols.length > 0 && <button className="btn-ghost whitespace-nowrap" onClick={() => refresh.mutate(wl.id)} disabled={refresh.isPending}>{refresh.isPending ? "Refreshing…" : "Refresh data"}</button>}
          <button className="btn-ghost hidden sm:inline-flex" onClick={() => api.logout().then(() => (window.location.href = "/login"))}>Log out</button>
        </>
      }
    >
      <div className="space-y-5">
        <DashboardPulse feed={feed.data} watchlist={wl} loading={feed.isLoading} error={feed.isError} />

        {watchlists.isError && (
          <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-400/30 bg-rose-400/[0.06] px-4 py-3 text-sm text-rose-100">
            <div>
              <p className="font-semibold">Market workspace could not load</p>
              <p className="mt-1 text-xs text-rose-200/80">
                {(watchlists.error as Error)?.message ?? "The API returned an unexpected error."}
              </p>
            </div>
            <div className="flex gap-2">
              {watchlists.isError && <button className="btn-ghost" onClick={() => watchlists.refetch()}>Retry watchlists</button>}
            </div>
          </div>
        )}

        <section className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.07] pb-4">
          <div><DashboardSectionHeader eyebrow="Current workspace" title={wl?.name ?? "Your watchlist"} detail={lastRefresh || feed.data?.generated_at ? `Last checked ${new Date(lastRefresh || feed.data!.generated_at).toLocaleTimeString()}` : "Waiting for the first market snapshot"} /></div>
          <div className="flex items-center gap-2"><AddSymbolDialog watchlistId={wl?.id ?? 0} />{autoRefresh && <span className="text-[11px] text-emerald-300">● Auto-refresh on</span>}</div>
        </section>

        {refresh.error && <div role="alert" className="flex w-fit max-w-full flex-wrap items-center gap-3 rounded-xl border border-rose-400/30 bg-rose-400/[0.06] px-4 py-2.5 text-sm text-rose-200"><span className="min-w-0 flex-1">Market data refresh failed: {(refresh.error as Error).message}</span>{wl && <button className="btn-ghost shrink-0" onClick={() => refresh.mutate(wl.id)}>Retry</button>}</div>}

        <section className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_minmax(0,1.35fr)]">
          <div className="order-2 space-y-5 2xl:order-1">
            {wl && wl.symbols.length > 0 && <WatchlistSnapshot symbols={wl.symbols} />}
            <PortfolioPanel />
          </div>

          <div className="order-1 min-w-0 space-y-4 2xl:order-2">
            <DashboardSectionHeader eyebrow="Prioritized signal queue" title="What deserves your attention" detail={feed.data?.since ? `Since your last check · ${new Date(feed.data.since).toLocaleString()}` : "Your first visit creates the comparison baseline"} action={<span className={`font-num rounded-full border px-2.5 py-1 text-xs ${cards.length ? "border-rose-400/25 bg-rose-400/10 text-rose-200" : "border-emerald-400/25 bg-emerald-400/10 text-emerald-200"}`}>{cards.length ? `${shown.length} of ${cards.length} signals` : "Quiet · 0 signals"}</span>} />
            {cards.length > 0 && presentTypes.length > 0 && <div className="flex gap-1.5 overflow-x-auto pb-1"><button className={`chip shrink-0 ${typeFilter === null ? "chip-on" : "chip-off"}`} onClick={() => setTypeFilter(null)}>All signals</button>{presentTypes.map((t) => <button key={t} className={`chip shrink-0 ${typeFilter === t ? "chip-on" : "chip-off"}`} onClick={() => setTypeFilter(t)}>{EVENT_META[t]?.icon ?? ""} {EVENT_META[t]?.label ?? t.replace(/_/g, " ")}</button>)}</div>}
            {cards.length > 0 && <div className="panel space-y-3 p-3">
              <div className="flex flex-col gap-2 sm:flex-row"><div className="relative min-w-0 flex-1"><input id="feed-search" className="input pr-14" placeholder="Search symbols, companies, or changes…" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search attention signals" /><kbd className="pointer-events-none absolute right-3 top-2 rounded border border-slate-700 bg-slate-900 px-1.5 py-0.5 text-[10px] text-slate-500">/</kbd></div><select className="input sm:w-44" value={sortBy} onChange={(e) => setSortBy(e.target.value as typeof sortBy)} aria-label="Sort attention feed"><option value="attention">Highest attention</option><option value="move">Biggest move</option><option value="recent">Most recent</option></select></div>
              <div className="flex flex-wrap items-center gap-2 text-xs"><button className={`chip ${savedOnly ? "chip-on" : "chip-off"}`} onClick={() => setSavedOnly(!savedOnly)}>★ Saved only</button><button className={`chip ${hideReviewed ? "chip-on" : "chip-off"}`} onClick={() => setHideReviewed(!hideReviewed)}>Hide reviewed</button><button className={`chip ${compact ? "chip-on" : "chip-off"}`} onClick={() => setCompact(!compact)}>Compact cards</button><button className={`chip ${autoRefresh ? "chip-on" : "chip-off"}`} onClick={() => setAutoRefresh(!autoRefresh)}>{autoRefresh ? "Auto-refresh on" : "Auto-refresh off"}</button><button className="chip chip-off" onClick={exportCsv} disabled={shown.length === 0}>Export CSV</button><span className="ml-auto text-slate-500">{shown.length} shown</span></div>
            </div>}
            {feed.isError ? <div className="rounded-xl border border-rose-400/25 bg-rose-400/[0.05] px-4 py-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-sm font-semibold text-rose-100">Signal feed unavailable</h2><p className="mt-1 text-xs text-slate-500">Your watchlist is safe. Retry when the API is available.</p></div><button className="btn-ghost" onClick={() => feed.refetch()}>Retry feed</button></div></div> : wl && wl.symbols.length === 0 ? <div className="panel border-dashed border-rose-400/30 p-8 text-center"><div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-rose-400/10 text-xl text-rose-300">+</div><h2 className="text-lg font-semibold">Start your market watch</h2><p className="mx-auto mt-1 max-w-md text-sm text-slate-400">Add your first symbol and we’ll build a baseline so the next refresh shows what meaningfully changed.</p><div className="mt-4"><AddSymbolDialog watchlistId={wl.id} /></div></div> : feed.isLoading ? <div className="space-y-3"><div className="skeleton h-20" /><div className="skeleton h-20" /></div> : cards.length === 0 ? <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/[0.04] p-6 sm:p-8"><div className="flex flex-wrap items-start gap-4"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-emerald-400/25 bg-emerald-400/10 text-lg text-emerald-300">✓</div><div className="min-w-0"><h2 className="text-base font-semibold text-slate-100">You’re caught up</h2><p className="mt-1 max-w-xl text-sm leading-relaxed text-slate-400">No meaningful changes were detected in your watchlist since the last check. When price, volume, news, or corporate events cross your attention bar, they’ll appear here.</p><div className="mt-4 flex flex-wrap gap-2"><button className="btn" onClick={() => wl && refresh.mutate(wl.id)} disabled={!wl || wl.symbols.length === 0 || refresh.isPending}>{refresh.isPending ? "Checking…" : "Check for changes"}</button>{wl && wl.symbols.length === 0 && <AddSymbolDialog watchlistId={wl.id} />}</div></div></div></div> : <AttentionFeed cards={shown} compact={compact} />}
          </div>
        </section>

        {wl && <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.65fr)]"><ReviewControls symbols={wl.symbols} watchlistId={wl.id} />{demoEnabled ? <div className="panel p-4"><DashboardSectionHeader eyebrow="Demo lab" title="Test a market story" detail="Use synthetic scenarios only when the mock provider is active." /><div className="flex flex-wrap gap-2">{scenarios.data?.map((sc) => <button key={sc.id} className={`scenario-chip ${scenario === sc.id ? "selected" : ""}`} onClick={() => setScenario(sc.id)}><div className="text-sm font-semibold">{sc.name}</div><div className="mt-0.5 max-w-56 text-[11px] text-slate-500">{sc.description}</div></button>)}</div><button className="btn mt-3" onClick={() => demo.mutate()} disabled={demo.isPending || wl.symbols.length === 0}>{demo.isPending ? "Running…" : `Run ${scenario.replace(/_/g, " ")}`}</button>{demo.data && <p className="mt-3 text-xs text-emerald-300"><b>Applied:</b> {demo.data.applied.length ? demo.data.applied.join(" · ") : "nothing — quiet day"}{demo.data.baseline_just_built && " · baseline built"}</p>}{demo.error && <p className="mt-3 text-xs text-rose-300">{(demo.error as Error).message}</p>}</div> : <div className="panel p-4"><DashboardSectionHeader eyebrow="Signal methodology" title="How the feed works" detail="Live provider active" /><p className="text-xs leading-relaxed text-slate-500">Every card carries trigger, baseline, source and confidence. Corroborated signals rank above lone technicals, and corporate events always surface. Data is labeled when delayed or stale.</p></div>}</section>}
      </div>
    </DashboardShell>
  );
}

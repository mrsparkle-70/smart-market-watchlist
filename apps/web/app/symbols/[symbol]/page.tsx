"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { PriceChart } from "@/components/PriceChart";
import { EventTimeline } from "@/components/EventTimeline";
import { AlertManager } from "@/components/AlertManager";
import { AnalyticsStrip } from "@/components/AnalyticsStrip";
import { AnalyticsPanel } from "@/components/AnalyticsPanel";
import { SymbolHeader } from "@/components/symbol/SymbolHeader";
import { SymbolMetricGrid } from "@/components/symbol/SymbolMetricGrid";
import { SymbolNewsList } from "@/components/symbol/SymbolNewsList";
import { SymbolEmpty, SymbolError, SymbolSkeleton } from "@/components/symbol/SymbolState";

export default function SymbolPage({ params }: { params: { symbol: string } }) {
  const symbol = decodeURIComponent(params.symbol).toUpperCase();
  const qc = useQueryClient();
  const [noteText, setNoteText] = useState("");
  const quote = useQuery({ queryKey: ["quote", symbol], queryFn: () => api.latest(symbol), retry: 1 });
  const history = useQuery({ queryKey: ["history", symbol], queryFn: () => api.history(symbol), retry: 1 });
  const analytics = useQuery({ queryKey: ["analytics", symbol], queryFn: () => api.analytics(symbol), retry: 1 });
  const events = useQuery({ queryKey: ["events", symbol], queryFn: () => api.events(symbol), retry: 1 });
  const news = useQuery({ queryKey: ["news", symbol], queryFn: () => api.news(symbol), retry: 1 });
  const note = useQuery({ queryKey: ["note", symbol], queryFn: () => api.note(symbol), retry: 1 });
  const refresh = useMutation({ mutationFn: async () => Promise.all([quote.refetch(), history.refetch(), analytics.refetch(), events.refetch(), news.refetch()]) });
  const saveNote = useMutation({ mutationFn: () => api.saveNote(symbol, noteText), onSuccess: () => qc.invalidateQueries({ queryKey: ["note", symbol] }) });

  useEffect(() => { if (note.data) setNoteText(note.data.body); }, [note.data]);

  return <main className="mx-auto max-w-[1440px] space-y-4 p-4 md:p-6 lg:space-y-5">
    <div className="flex items-center justify-between gap-3"><Link href="/dashboard" className="text-sm text-slate-400 transition hover:text-rose-200">← Back to dashboard</Link><span className="hidden font-num text-[11px] uppercase tracking-[0.16em] text-slate-600 sm:block">Decision workspace / v1</span></div>
    <SymbolHeader symbol={symbol} quote={quote.data} onRefresh={() => refresh.mutate()} refreshing={refresh.isPending} />
    {quote.isError && <SymbolError title={`Latest quote for ${symbol} could not be loaded`} error={quote.error} onRetry={() => quote.refetch()} />}
    <SymbolMetricGrid quote={quote.data} />

    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.65fr)_minmax(300px,.75fr)]">
      <section className="panel min-w-0 overflow-hidden p-4 sm:p-5"><div className="mb-4 flex flex-wrap items-end justify-between gap-3"><div><div className="kpi-label">Price action</div><h2 className="mt-1 text-lg font-semibold text-white">Historical signal</h2></div><span className="text-xs text-slate-500">{history.data?.length ?? 0} stored observations</span></div>{analytics.data && analytics.data.observations > 0 && <div className="mb-5"><AnalyticsStrip data={analytics.data} /></div>}{history.isLoading ? <SymbolSkeleton className="h-[320px]" /> : history.isError ? <SymbolError title="Historical prices unavailable" error={history.error} onRetry={() => history.refetch()} /> : <PriceChart candles={history.data ?? []} />}{analytics.isError && <p className="mt-3 text-xs text-amber-300">Analytics are temporarily unavailable; the chart can still be explored.</p>}</section>
      <section className="panel min-w-0 p-4 sm:p-5"><div className="mb-4"><div className="kpi-label">Signal monitor</div><h2 className="mt-1 text-lg font-semibold text-white">Detected changes</h2><p className="mt-1 text-xs leading-relaxed text-slate-500">Events are ranked by attention, confidence, and corroborating evidence.</p></div>{events.isLoading ? <div className="space-y-3"><SymbolSkeleton className="h-16" /><SymbolSkeleton className="h-16" /></div> : events.isError ? <SymbolError title="Event history unavailable" error={events.error} onRetry={() => events.refetch()} /> : events.data?.length ? <EventTimeline events={events.data} /> : <SymbolEmpty title="No detected changes" detail="The monitor has not found a meaningful event for this symbol yet." />}</section>
    </div>

    <AnalyticsPanel symbol={symbol} candles={history.data ?? []} />

    <div className="grid gap-4 lg:grid-cols-2">
      <section className="panel min-w-0 p-4 sm:p-5"><div className="mb-4 flex items-end justify-between gap-3"><div><div className="kpi-label">Information flow</div><h2 className="mt-1 text-lg font-semibold text-white">Scored news</h2></div><span className="text-xs text-slate-500">Provider-ranked</span></div><SymbolNewsList news={news.data} loading={news.isLoading} error={news.error} onRetry={() => news.refetch()} /></section>
      <section className="min-w-0"><div className="mb-3 px-1"><div className="kpi-label">Your controls</div><p className="mt-1 text-xs text-slate-500">Thresholds are checked on the next successful watchlist refresh.</p></div><AlertManager symbol={symbol} /></section>
    </div>

    <section className="panel p-4 sm:p-5"><div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start"><div><div className="kpi-label">Private context</div><h2 className="mt-1 text-lg font-semibold text-white">Decision journal</h2><p className="mt-1 text-xs leading-relaxed text-slate-500">Capture the reason you are watching {symbol} and the evidence that would change your mind.</p></div><button className="btn shrink-0" disabled={saveNote.isPending || note.isLoading} onClick={() => saveNote.mutate()}>{saveNote.isPending ? "Saving…" : saveNote.isSuccess ? "Saved ✓" : "Save thesis"}</button></div><textarea className="input mt-4 min-h-32 resize-y" maxLength={5000} placeholder="Example: Watching for margin recovery after the next earnings report…" value={noteText} onChange={(e) => setNoteText(e.target.value)} aria-label={`Decision journal for ${symbol}`} /><div className="mt-1 flex justify-between text-[11px] text-slate-500"><span>{note.isError ? "Could not load your existing note." : note.data?.updated_at ? `Last saved ${new Date(note.data.updated_at).toLocaleString()}` : "Only you can see this note."}</span><span>{noteText.length}/5000</span></div>{saveNote.error && <p className="mt-2 text-xs text-rose-300">Could not save note: {(saveNote.error as Error).message}</p>}</section>
  </main>;
}

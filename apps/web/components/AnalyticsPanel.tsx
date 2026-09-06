"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { createChart, ColorType } from "lightweight-charts";
import { api } from "@/lib/api";
import type { Candle } from "@/lib/types";

type Tab = "relative" | "drawdown" | "volatility";

const VOL_WINDOW = 20;
const TRADING_DAYS = 252;

/** One close per UTC day (the day's LAST snapshot wins; input must be ascending). */
function dailyCloses(candles: Candle[]): { day: string; close: number }[] {
  const byDay = new Map<string, number>();
  candles.forEach((c) => {
    const ts = new Date(c.ts).getTime();
    if (!Number.isFinite(ts) || !Number.isFinite(c.close)) return;
    byDay.set(new Date(ts).toISOString().slice(0, 10), c.close);
  });
  return Array.from(byDay.entries())
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([day, close]) => ({ day, close }));
}

/** Running-peak drawdown in % (#47). */
function drawdownSeries(daily: { day: string; close: number }[]) {
  let peak = -Infinity;
  const out: { time: string; value: number }[] = [];
  let maxDd = { time: "", value: 0 };
  for (const { day, close } of daily) {
    peak = Math.max(peak, close);
    const dd = (close / peak - 1) * 100;
    out.push({ time: day, value: Math.round(dd * 1000) / 1000 });
    if (dd < maxDd.value) maxDd = { time: day, value: dd };
  }
  return { points: out, maxDd, current: out.length ? out[out.length - 1].value : 0 };
}

/** Rolling annualized volatility of daily returns (#48). */
function volatilitySeries(daily: { day: string; close: number }[]) {
  const returns: number[] = [];
  for (let i = 1; i < daily.length; i++) returns.push(daily[i].close / daily[i - 1].close - 1);
  const out: { time: string; value: number }[] = [];
  for (let i = VOL_WINDOW - 1; i < returns.length; i++) {
    const win = returns.slice(i - VOL_WINDOW + 1, i + 1);
    const mean = win.reduce((a, b) => a + b, 0) / win.length;
    const variance = win.reduce((a, b) => a + (b - mean) ** 2, 0) / (win.length - 1);
    const annualized = Math.sqrt(variance) * Math.sqrt(TRADING_DAYS) * 100;
    out.push({ time: daily[i + 1].day, value: Math.round(annualized * 10) / 10 });
  }
  const max = out.reduce((m, p) => (p.value > m.value ? p : m), { time: "", value: 0 });
  return { points: out, current: out.length ? out[out.length - 1].value : 0, max };
}

export function AnalyticsPanel({ symbol, candles }: { symbol: string; candles: Candle[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const [tab, setTab] = useState<Tab>("relative");
  const relative = useQuery({
    queryKey: ["relative", symbol],
    queryFn: () => api.relative(symbol),
    retry: 1,
  });

  const daily = useMemo(() => dailyCloses(candles), [candles]);
  const dd = useMemo(() => drawdownSeries(daily), [daily]);
  const vol = useMemo(() => volatilitySeries(daily), [daily]);
  const hasDaily = daily.length >= 2;

  useEffect(() => {
    if (!ref.current) return;
    if (tab !== "relative" && !hasDaily) return;
    if (tab === "relative" && (!relative.data || relative.data.points.length < 2)) return;

    const chart = createChart(ref.current, {
      width: ref.current.clientWidth,
      height: 260,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: "#9ca3af" },
      grid: { vertLines: { color: "#1f2937" }, horzLines: { color: "#1f2937" } },
      timeScale: { timeVisible: false },
    });

    if (tab === "relative") {
      const points = relative.data!.points;
      const sym = chart.addLineSeries({ color: "#f0445e", lineWidth: 2, title: symbol });
      sym.setData(points.map((p) => ({ time: p.date, value: p.symbol_pct })));
      const bench = chart.addLineSeries({ color: "#38bdf8", lineWidth: 2, title: relative.data!.benchmark });
      bench.setData(points.map((p) => ({ time: p.date, value: p.benchmark_pct })));
    } else if (tab === "drawdown") {
      const area = chart.addAreaSeries({
        lineColor: "#f0445e",
        topColor: "rgba(240,68,94,0.3)",
        bottomColor: "rgba(240,68,94,0.02)",
        lineWidth: 2,
      });
      area.setData(dd.points);
    } else {
      const line = chart.addLineSeries({ color: "#f59e0b", lineWidth: 2, title: `${VOL_WINDOW}d ann.` });
      line.setData(vol.points);
    }

    chart.timeScale().fitContent();
    const onResize = () => chart.applyOptions({ width: ref.current?.clientWidth });
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
    };
  }, [tab, hasDaily, relative.data, dd.points, vol.points, symbol]);

  const tabBtn = (t: Tab, label: string) => (
    <button
      key={t}
      className={`rounded-md px-2 py-1 text-[11px] ${tab === t ? "bg-rose-400/15 text-rose-200" : "text-slate-500 hover:text-slate-200"}`}
      onClick={() => setTab(t)}
    >
      {label}
    </button>
  );

  const lastRel = relative.data?.points[relative.data.points.length - 1];
  const chartBody =
    tab === "relative" ? (
      relative.isLoading ? (
        <div className="flex h-[260px] items-center justify-center text-sm text-slate-500">Loading benchmark comparison…</div>
      ) : relative.isError ? (
        <div className="flex h-[260px] items-center justify-center text-sm text-slate-500">Benchmark data unavailable.</div>
      ) : lastRel ? (
        <div ref={ref} className="w-full overflow-hidden rounded-xl" />
      ) : (
        <div className="flex h-[260px] items-center justify-center text-sm text-slate-500">
          Not enough overlapping {symbol} / benchmark history yet.
        </div>
      )
    ) : !hasDaily ? (
      <div className="flex h-[260px] items-center justify-center text-sm text-slate-500">
        Chart appears once at least two days of snapshots accumulate.
      </div>
    ) : (
      <div ref={ref} className="w-full overflow-hidden rounded-xl" />
    );

  return (
    <section className="panel min-w-0 p-4 sm:p-5">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="kpi-label">Risk &amp; performance</div>
          <h2 className="mt-1 text-lg font-semibold text-white">Analytics</h2>
        </div>
        <div className="flex flex-wrap items-center gap-1">
          {tabBtn("relative", `vs ${relative.data?.benchmark ?? "SPY"}`)}
          {tabBtn("drawdown", "Drawdown")}
          {tabBtn("volatility", "Volatility")}
        </div>
      </div>

      {tab === "drawdown" && hasDaily && (
        <div className="mb-3 flex flex-wrap gap-6 text-sm">
          <span className="text-slate-400">
            Current drawdown <b className={dd.current < 0 ? "text-rose-300" : "text-emerald-300"}>{dd.current.toFixed(2)}%</b>
          </span>
          <span className="text-slate-400">
            Max drawdown <b className="text-rose-300">{dd.maxDd.value.toFixed(2)}%</b>
            {dd.maxDd.time && <span className="text-slate-600"> ({dd.maxDd.time})</span>}
          </span>
        </div>
      )}
      {tab === "volatility" && hasDaily && (
        <div className="mb-3 flex flex-wrap gap-6 text-sm">
          <span className="text-slate-400">
            Current ({VOL_WINDOW}d, annualized) <b className="text-amber-300">{vol.current.toFixed(1)}%</b>
          </span>
          <span className="text-slate-400">
            Peak <b className="text-amber-300">{vol.max.value.toFixed(1)}%</b>
            {vol.max.time && <span className="text-slate-600"> ({vol.max.time})</span>}
          </span>
          {vol.points.length === 0 && <span className="text-slate-500">Needs {VOL_WINDOW + 1} days of data.</span>}
        </div>
      )}
      {tab === "relative" && lastRel && (
        <div className="mb-3 flex flex-wrap gap-6 text-sm">
          <span className="text-slate-400">
            {symbol} <b className="text-rose-300">{lastRel.symbol_pct >= 0 ? "+" : ""}{lastRel.symbol_pct.toFixed(1)}%</b>
          </span>
          <span className="text-slate-400">
            {relative.data!.benchmark} <b className="text-sky-300">{lastRel.benchmark_pct >= 0 ? "+" : ""}{lastRel.benchmark_pct.toFixed(1)}%</b>
          </span>
          <span className="text-slate-600">over {relative.data!.days}d, rebased to 0%</span>
        </div>
      )}

      {chartBody}
    </section>
  );
}

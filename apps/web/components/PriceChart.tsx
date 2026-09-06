"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { createChart, ColorType } from "lightweight-charts";
import type { Candle } from "@/lib/types";

/** Simple moving average over chart points; series starts once the window fills. */
function sma(data: { time: number; close: number }[], window: number) {
  if (data.length < window) return [];
  const out: { time: never; value: number }[] = [];
  let sum = 0;
  for (let i = 0; i < data.length; i++) {
    sum += data[i].close;
    if (i >= window) sum -= data[i - window].close;
    if (i >= window - 1) out.push({ time: data[i].time as never, value: sum / window });
  }
  return out;
}

export function PriceChart({ candles }: { candles: Candle[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const [range, setRange] = useState<"1M" | "3M" | "1Y" | "ALL">("3M");
  const [showVolume, setShowVolume] = useState(true);
  const [showMa20, setShowMa20] = useState(true);
  const [showMa50, setShowMa50] = useState(true);
  const chartCandles = useMemo(() => {
    if (range === "ALL") return candles;
    const days = range === "1M" ? 30 : range === "3M" ? 90 : 365;
    const cutoff = Date.now() - days * 86_400_000;
    return candles.filter((c) => new Date(c.ts).getTime() >= cutoff);
  }, [candles, range]);

  // Duplicate-safe ingestion (#42): providers can return duplicate candles or
  // millisecond timestamps; lightweight-charts requires strictly ascending,
  // unique times, so keep one observation per second (newest wins).
  const chartData = useMemo(() => {
    const byTime = new Map<number, { time: never; close: number; volume: number | null }>();
    chartCandles.forEach((c) => {
      const time = Math.floor(new Date(c.ts).getTime() / 1000);
      if (!Number.isFinite(time) || !Number.isFinite(c.close)) return;
      byTime.set(time, { time: time as never, close: c.close, volume: c.volume });
    });
    return Array.from(byTime.values()).sort((a, b) => (a.time as number) - (b.time as number));
  }, [chartCandles]);

  // Volume bars are colored by direction vs the previous deduped point (#43).
  const volumeData = useMemo(
    () =>
      chartData.map((d, i) => {
        const prev = i > 0 ? chartData[i - 1].close : d.close;
        const up = d.close >= prev;
        return {
          time: d.time,
          value: d.volume ?? 0,
          color: up ? "rgba(16,185,129,0.35)" : "rgba(240,68,94,0.35)",
        };
      }),
    [chartData],
  );

  const ma20 = useMemo(() => sma(chartData, 20), [chartData]);
  const ma50 = useMemo(() => sma(chartData, 50), [chartData]);


  useEffect(() => {
    if (!ref.current || chartData.length === 0) return;

    const chart = createChart(ref.current, {
      width: ref.current.clientWidth,
      height: 320,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: "#9ca3af" },
      grid: { vertLines: { color: "#1f2937" }, horzLines: { color: "#1f2937" } },
      timeScale: { timeVisible: true },
    });
    const priceSeries = chart.addAreaSeries({
      lineColor: "#f0445e",
      topColor: "rgba(240,68,94,0.3)",
      bottomColor: "rgba(240,68,94,0.02)",
      lineWidth: 2,
    });
    priceSeries.setData(chartData.map((d) => ({ time: d.time, value: d.close })));
    // Leave the bottom quarter of the pane for the volume histogram.
    priceSeries.priceScale().applyOptions({ scaleMargins: { top: 0.1, bottom: showVolume ? 0.25 : 0.05 } });

    if (showVolume) {
      const volumeSeries = chart.addHistogramSeries({
        priceFormat: { type: "volume" },
        priceScaleId: "volume",
        lastValueVisible: false,
        priceLineVisible: false,
      });
      volumeSeries.setData(volumeData);
      volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    }
    if (showMa20 && ma20.length > 0) {
      const line = chart.addLineSeries({ color: "#f59e0b", lineWidth: 1, lastValueVisible: false, priceLineVisible: false, title: "MA20" });
      line.setData(ma20);
    }
    if (showMa50 && ma50.length > 0) {
      const line = chart.addLineSeries({ color: "#38bdf8", lineWidth: 1, lastValueVisible: false, priceLineVisible: false, title: "MA50" });
      line.setData(ma50);
    }

    chart.timeScale().fitContent();
    const onResize = () => chart.applyOptions({ width: ref.current?.clientWidth });
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
    };
  }, [chartData, volumeData, ma20, ma50, showVolume, showMa20, showMa50]);

  if (candles.length === 0) {
    return (
      <div className="card flex h-64 items-center justify-center text-sm text-gray-500">
        Chart appears once snapshot history accumulates.
      </div>
    );
  }
  const toggle = (active: boolean) =>
    `rounded-md px-2 py-1 text-[11px] ${active ? "bg-rose-400/15 text-rose-200" : "text-slate-500 hover:text-slate-200"}`;
  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-2">
        <span className="text-xs text-slate-500">{chartCandles.length} observations</span>
        <div className="flex flex-wrap items-center justify-end gap-1">
          <button className={toggle(showVolume)} onClick={() => setShowVolume(!showVolume)}>Volume</button>
          <button className={toggle(showMa20)} onClick={() => setShowMa20(!showMa20)} aria-label="Toggle 20-period moving average">MA20</button>
          <button className={toggle(showMa50)} onClick={() => setShowMa50(!showMa50)} aria-label="Toggle 50-period moving average">MA50</button>
          <span className="mx-1 text-slate-700">|</span>
          {(["1M", "3M", "1Y", "ALL"] as const).map((item) => (
            <button key={item} className={toggle(range === item)} onClick={() => setRange(item)}>{item}</button>
          ))}
        </div>
      </div>
      {chartData.length > 0 ? (
        <div ref={ref} className="w-full overflow-hidden rounded-xl" />
      ) : (
        <div className="flex h-64 items-center justify-center text-sm text-slate-500">No observations in this range.</div>
      )}
    </div>
  );
}

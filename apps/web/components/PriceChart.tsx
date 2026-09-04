"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { createChart, ColorType } from "lightweight-charts";
import type { Candle } from "@/lib/types";

export function PriceChart({ candles }: { candles: Candle[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const [range, setRange] = useState<"1M" | "3M" | "1Y" | "ALL">("3M");
  const chartCandles = useMemo(() => {
    if (range === "ALL") return candles;
    const days = range === "1M" ? 30 : range === "3M" ? 90 : 365;
    const cutoff = Date.now() - days * 86_400_000;
    return candles.filter((c) => new Date(c.ts).getTime() >= cutoff);
  }, [candles, range]);

  useEffect(() => {
    if (!ref.current || chartCandles.length === 0) return;

    // Providers can return duplicate candles (or timestamps with milliseconds).
    // lightweight-charts requires strictly ascending, unique timestamps.
    const byTime = new Map<number, number>();
    chartCandles.forEach((c) => {
      const time = Math.floor(new Date(c.ts).getTime() / 1000);
      if (Number.isFinite(time) && Number.isFinite(c.close)) byTime.set(time, c.close);
    });
    const chartData = Array.from(byTime.entries())
      .sort(([a], [b]) => a - b)
      .map(([time, value]) => ({ time: time as never, value }));
    if (chartData.length === 0) return;

    const chart = createChart(ref.current, {
      width: ref.current.clientWidth,
      height: 320,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: "#9ca3af" },
      grid: { vertLines: { color: "#1f2937" }, horzLines: { color: "#1f2937" } },
      timeScale: { timeVisible: true },
    });
    const series = chart.addAreaSeries({
      lineColor: "#f0445e",
      topColor: "rgba(240,68,94,0.3)",
      bottomColor: "rgba(240,68,94,0.02)",
      lineWidth: 2,
    });
    series.setData(chartData);
    chart.timeScale().fitContent();
    const onResize = () => chart.applyOptions({ width: ref.current?.clientWidth });
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
    };
  }, [chartCandles]);

  if (candles.length === 0) {
    return (
      <div className="card flex h-64 items-center justify-center text-sm text-gray-500">
        Chart appears once snapshot history accumulates.
      </div>
    );
  }
  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-2">
        <span className="text-xs text-slate-500">{chartCandles.length} observations</span>
        <div className="flex gap-1">
          {(["1M", "3M", "1Y", "ALL"] as const).map((item) => (
            <button key={item} className={`rounded-md px-2 py-1 text-[11px] ${range === item ? "bg-rose-400/15 text-rose-200" : "text-slate-500 hover:text-slate-200"}`} onClick={() => setRange(item)}>{item}</button>
          ))}
        </div>
      </div>
      {chartCandles.length > 0 ? <div ref={ref} className="w-full overflow-hidden rounded-xl" /> : <div className="flex h-64 items-center justify-center text-sm text-slate-500">No observations in this range.</div>}
    </div>
  );
}

"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PriceAlert } from "@/lib/types";

const LABELS: Record<PriceAlert["condition"], string> = {
  price_above: "Price rises above",
  price_below: "Price falls below",
  move_up: "Daily move reaches +",
  move_down: "Daily move reaches −",
};

export function AlertManager({ symbol }: { symbol: string }) {
  const qc = useQueryClient();
  const [condition, setCondition] = useState<PriceAlert["condition"]>("price_above");
  const [threshold, setThreshold] = useState("");
  const alerts = useQuery({ queryKey: ["alerts", symbol], queryFn: () => api.alerts(symbol) });
  const create = useMutation({
    mutationFn: () => api.createAlert(symbol, condition, Number(threshold)),
    onSuccess: () => { setThreshold(""); qc.invalidateQueries({ queryKey: ["alerts", symbol] }); },
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.deleteAlert(symbol, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts", symbol] }),
  });
  const isPercent = condition === "move_up" || condition === "move_down";

  return (
    <section className="panel p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">Personal alerts</h3>
          <p className="mt-1 text-xs text-slate-500">Checked whenever this symbol refreshes.</p>
        </div>
        <span className="chip chip-off">{alerts.data?.length ?? 0} active</span>
      </div>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <select className="input sm:flex-1" value={condition} onChange={(e) => setCondition(e.target.value as PriceAlert["condition"])}>
          {Object.entries(LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <div className="flex gap-2 sm:w-48">
          <input className="input" type="number" min="0.01" step="0.01" placeholder={isPercent ? "e.g. 5" : "e.g. 250"} value={threshold} onChange={(e) => setThreshold(e.target.value)} />
          <span className="self-center text-xs text-slate-500">{isPercent ? "%" : "USD"}</span>
        </div>
        <button className="btn shrink-0" disabled={!threshold || Number(threshold) <= 0 || create.isPending} onClick={() => create.mutate()}>Add alert</button>
      </div>
      {create.error && <p className="mt-2 text-xs text-rose-300">{(create.error as Error).message}</p>}
      {alerts.data && alerts.data.length > 0 && (
        <ul className="mt-3 space-y-2">
          {alerts.data.map((alert) => (
            <li key={alert.id} className="flex items-center justify-between gap-3 rounded-lg border b-line bg-slate-950/30 px-3 py-2 text-sm">
              <span>{LABELS[alert.condition]} <b className="font-num">{alert.condition.startsWith("move_") ? `${alert.threshold}%` : `$${alert.threshold.toFixed(2)}`}</b></span>
              <span className="flex items-center gap-3">
                <span className="text-xs text-slate-500">{alert.last_triggered_at ? `Triggered ${new Date(alert.last_triggered_at).toLocaleString()}` : "Waiting"}</span>
                <button className="text-xs text-slate-500 hover:text-rose-300" onClick={() => remove.mutate(alert.id)}>Remove</button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

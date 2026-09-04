"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const qc = useQueryClient();
  const prefs = useQuery({ queryKey: ["preferences"], queryFn: api.preferences });
  const [price, setPrice] = useState("");
  const [volume, setVolume] = useState("");
  const [volatility, setVolatility] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (prefs.data) {
      setPrice(String(prefs.data.price_threshold));
      setVolume(String(prefs.data.volume_threshold));
      setVolatility(String(prefs.data.volatility_threshold));
    }
  }, [prefs.data]);

  const save = useMutation({
    mutationFn: () =>
      api.updatePreferences({
        price_threshold: Number(price),
        volume_threshold: Number(volume),
        volatility_threshold: Number(volatility),
      }),
    onSuccess: () => { setSaved(true); setTimeout(() => setSaved(false), 2000); },
  });

  return (
    <main className="mx-auto max-w-2xl space-y-4 p-6">
      <a href="/dashboard" className="text-sm text-gray-400 hover:text-gray-200">← Back to dashboard</a>
      <h1 className="text-2xl font-bold">Alert thresholds</h1>
      <p className="text-sm text-gray-400">
        A change is only meaningful relative to YOUR tolerance. These thresholds feed the attention score.
      </p>
      <div className="card space-y-3">
        <label className="block text-sm">
          Price move threshold (%):{" "}
          <input className="input mt-1" type="number" step="0.5" min="0.5" value={price}
                 onChange={(e) => setPrice(e.target.value)} />
        </label>
        <label className="block text-sm">
          Volume ratio threshold (× normal):{" "}
          <input className="input mt-1" type="number" step="0.1" min="1" value={volume}
                 onChange={(e) => setVolume(e.target.value)} />
        </label>
        <label className="block text-sm">
          Volatility expansion threshold (× baseline):{" "}
          <input className="input mt-1" type="number" step="0.1" min="1" value={volatility}
                 onChange={(e) => setVolatility(e.target.value)} />
        </label>
        <button className="btn" disabled={save.isPending} onClick={() => save.mutate()}>
          {saved ? "Saved ✓" : "Save thresholds"}
        </button>
      </div>
    </main>
  );
}

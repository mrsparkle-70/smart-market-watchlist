"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { NotificationChannel } from "@/lib/types";

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

      <NotificationSettings />
    </main>
  );
}

function NotificationSettings() {
  const qc = useQueryClient();
  const notifPrefs = useQuery({ queryKey: ["notif-prefs"], queryFn: api.notificationPreferences });
  const channels = useQuery({ queryKey: ["channels"], queryFn: api.notificationChannels });
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [email, setEmail] = useState("");
  const [qhs, setQhs] = useState("");
  const [qhe, setQhe] = useState("");

  useEffect(() => {
    if (notifPrefs.data) {
      setQhs(notifPrefs.data.quiet_hours_start?.slice(0, 5) ?? "");
      setQhe(notifPrefs.data.quiet_hours_end?.slice(0, 5) ?? "");
    }
  }, [notifPrefs.data]);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["notif-prefs"] });
    qc.invalidateQueries({ queryKey: ["channels"] });
  };

  const flash = (message: string) => { setNotice(message); setError(""); setTimeout(() => setNotice(""), 4000); };
  const fail = (err: unknown) => { setError(err instanceof Error ? err.message : String(err)); setNotice(""); };

  const updatePrefs = useMutation({
    mutationFn: (p: Parameters<typeof api.updateNotificationPreferences>[0]) => api.updateNotificationPreferences(p),
    onSuccess: invalidate,
    onError: fail,
  });

  const addEmail = useMutation({
    mutationFn: () => api.addEmailChannel(email.trim()),
    onSuccess: () => { setEmail(""); invalidate(); flash("Email channel added. It stays unverified until you confirm it."); },
    onError: fail,
  });

  const toggleChannel = useMutation({
    mutationFn: (c: NotificationChannel) => api.toggleChannel(c.id, !c.enabled),
    onSuccess: invalidate,
    onError: fail,
  });

  const removeChannel = useMutation({
    mutationFn: (id: number) => api.removeChannel(id),
    onSuccess: invalidate,
    onError: fail,
  });

  const testChannel = useMutation({
    mutationFn: (id: number) => api.testChannel(id),
    onSuccess: (r) => flash(r.delivered_in_this_call > 0 ? "Test delivered ✓" : "Test queued — it will go out with the next worker cycle."),
    onError: fail,
  });

  const enablePush = useMutation({
    mutationFn: subscribeBrowserPush,
    onSuccess: () => { invalidate(); flash("Browser push enabled ✓"); },
    onError: fail,
  });

  const list = channels.data ?? [];

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-bold">Notifications</h1>
      <p className="text-sm text-gray-400">
        How (and when) alerts reach you. Email must be confirmed; browser push is verified as soon as you grant permission.
      </p>

      {error && <p className="rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">{error}</p>}
      {notice && <p className="rounded-lg border border-emerald-400/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">{notice}</p>}

      <div className="card space-y-3">
        <h2 className="text-sm font-semibold tracking-wide text-gray-200">Delivery</h2>
        <ToggleRow
          label="Notifications"
          description="Master switch. When off, no alerts are delivered on any channel."
          checked={notifPrefs.data?.notification_enabled ?? true}
          disabled={notifPrefs.isLoading || updatePrefs.isPending}
          onChange={(v) => updatePrefs.mutate({ notification_enabled: v })}
        />
        <ToggleRow
          label="Daily digest"
          description="Batch non-urgent alerts into one email per day instead of firing immediately."
          checked={notifPrefs.data?.daily_digest ?? false}
          disabled={notifPrefs.isLoading || updatePrefs.isPending}
          onChange={(v) => updatePrefs.mutate({ daily_digest: v })}
        />
        <div className="flex flex-wrap items-end gap-3">
          <label className="block text-sm">
            Quiet hours start
            <input className="input mt-1" type="time" value={qhs} onChange={(e) => setQhs(e.target.value)} />
          </label>
          <label className="block text-sm">
            Quiet hours end
            <input className="input mt-1" type="time" value={qhe} onChange={(e) => setQhe(e.target.value)} />
          </label>
          <button
            className="btn-ghost"
            disabled={updatePrefs.isPending}
            onClick={() => updatePrefs.mutate({ quiet_hours_start: qhs || undefined, quiet_hours_end: qhe || undefined })}
          >
            Save quiet hours
          </button>
        </div>
        <p className="text-xs text-gray-500">
          Overnight windows (e.g. 22:00 → 07:00) are handled correctly. Leave both empty to disable.
        </p>
      </div>

      <div className="card space-y-3">
        <h2 className="text-sm font-semibold tracking-wide text-gray-200">Channels</h2>

        {channels.isLoading && <p className="text-sm text-gray-500">Loading channels…</p>}
        {!channels.isLoading && list.length === 0 && (
          <p className="text-sm text-gray-500">No channels yet. Add an email or enable browser push below.</p>
        )}

        {list.map((c) => (
          <div key={c.id} className="flex flex-wrap items-center gap-2 rounded-lg border border-white/10 px-3 py-2">
            <span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-gray-300">
              {c.kind === "webpush" ? "Browser push" : "Email"}
            </span>
            <span className="truncate text-sm text-gray-200">{c.kind === "webpush" ? "This browser" : c.target}</span>
            {!c.verified && <span className="text-[10px] uppercase text-amber-400">unverified</span>}
            {!c.enabled && <span className="text-[10px] uppercase text-gray-500">off</span>}
            <span className="ml-auto flex items-center gap-1.5">
              <button className="btn-ghost text-xs" disabled={testChannel.isPending} onClick={() => testChannel.mutate(c.id)}>
                Test
              </button>
              <button className="btn-ghost text-xs" onClick={() => toggleChannel.mutate(c)}>
                {c.enabled ? "Disable" : "Enable"}
              </button>
              <button className="btn-ghost text-xs text-rose-300" onClick={() => removeChannel.mutate(c.id)}>
                Remove
              </button>
            </span>
          </div>
        ))}

        <div className="flex flex-wrap items-end gap-2 pt-1">
          <label className="block min-w-56 flex-1 text-sm">
            Add email channel
            <input
              className="input mt-1"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && email.includes("@")) addEmail.mutate(); }}
            />
          </label>
          <button className="btn" disabled={!email.includes("@") || addEmail.isPending} onClick={() => addEmail.mutate()}>
            Add email
          </button>
        </div>

        <div className="pt-1">
          <button className="btn" disabled={enablePush.isPending} onClick={() => enablePush.mutate()}>
            {enablePush.isPending ? "Requesting permission…" : "Enable browser push"}
          </button>
          <p className="mt-1 text-xs text-gray-500">
            Uses your browser&apos;s notification permission. Push subscriptions are verified immediately.
          </p>
        </div>
      </div>
    </section>
  );
}

function ToggleRow({ label, description, checked, disabled, onChange }: {
  label: string;
  description: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-start gap-3 text-sm">
      <input
        type="checkbox"
        className="mt-1 h-4 w-4 accent-emerald-500"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span>
        <span className="block font-medium text-gray-200">{label}</span>
        <span className="block text-xs text-gray-500">{description}</span>
      </span>
    </label>
  );
}

/** Ask the browser for push permission, register the SW, and POST the subscription. */
async function subscribeBrowserPush(): Promise<void> {
  if (typeof window === "undefined" || !("serviceWorker" in navigator) || !("PushManager" in window)) {
    throw new Error("This browser does not support web push");
  }
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error("Notification permission was not granted");
  }
  const { publicKey } = await api.vapidPublicKey();
  const reg = await navigator.serviceWorker.register("/sw.js");
  await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  });
  const json = sub.toJSON();
  if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
    throw new Error("Browser returned an incomplete push subscription");
  }
  await api.addWebPushChannel(
    json.endpoint,
    { p256dh: json.keys.p256dh as string, auth: json.keys.auth as string }
  );
}

function urlBase64ToUint8Array(base64String: string) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; ++i) output[i] = raw.charCodeAt(i);
  return output;
}

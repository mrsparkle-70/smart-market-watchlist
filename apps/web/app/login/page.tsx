"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(register: boolean) {
    setBusy(true);
    setError("");
    try {
      if (register) await api.register(email, password);
      else await api.login(email, password);
      router.push("/dashboard");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden p-4 sm:p-6">
      <div className="pointer-events-none absolute -left-24 -top-24 h-72 w-72 rounded-full bg-rose-500/10 blur-3xl" />
      <div className="card relative w-full max-w-md p-6 sm:p-8">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-rose-500 to-orange-400 font-black text-white">MW</div>
          <div>
            <div className="kpi-label">Market intelligence</div>
            <h1 className="text-xl font-bold">Smart Market Watchlist</h1>
          </div>
        </div>
        <p className="mt-1 text-sm text-slate-400">
          See what meaningfully changed since you last checked — and what deserves your attention now.
        </p>
        <div className="mt-6 space-y-3">
          <input className="input" type="email" placeholder="Email" value={email}
                 onChange={(e) => setEmail(e.target.value)} />
          <input className="input" type="password" placeholder="Password (min 8 chars)" value={password}
                 onChange={(e) => setPassword(e.target.value)} />
          {error && <p className="text-sm text-red-400">{error}</p>}
          <div className="flex gap-2">
            <button className="btn flex-1" disabled={busy || !email || !password} onClick={() => submit(false)}>
              Log in
            </button>
            <button className="btn-ghost flex-1" disabled={busy || !email || !password} onClick={() => submit(true)}>
              Create account
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}

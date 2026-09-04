export function DashboardShell({
  children,
  watchlistName,
  symbolCount,
  provider,
  actions,
}: {
  children: React.ReactNode;
  watchlistName?: string;
  symbolCount: number;
  provider?: string;
  actions: React.ReactNode;
}) {
  const providerLabel = provider === "mock" ? "Demo data" : provider ? `${provider} feed` : "Connecting";

  return (
    <div className="min-h-screen bg-[var(--bg)]">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.07] pb-3">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-rose-300/80">Live market workspace</p>
          <p className="truncate text-sm text-slate-300">{watchlistName ?? "Your watchlist"} · {symbolCount} symbols · {providerLabel}</p>
        </div>
        <div className="flex w-full flex-wrap items-center justify-start gap-2 sm:w-auto sm:flex-nowrap sm:justify-end">{actions}</div>
      </div>
      {children}
    </div>
  );
}

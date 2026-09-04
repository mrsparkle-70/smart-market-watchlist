const STYLES: Record<string, { label: string; cls: string }> = {
  fresh: { label: "Fresh", cls: "bg-emerald-900/50 text-emerald-300 border-emerald-700" },
  delayed: { label: "Delayed", cls: "bg-amber-900/50 text-amber-300 border-amber-700" },
  stale: { label: "Stale", cls: "bg-red-900/50 text-red-300 border-red-700" },
  unknown: { label: "Freshness unknown", cls: "bg-gray-800 text-gray-400 border-gray-700" },
};

export function DataFreshnessBadge({ freshness, marketStatus }: { freshness: string; marketStatus?: string }) {
  const s = STYLES[freshness] ?? STYLES.unknown;
  const sessionLabel = marketStatus === "pre" ? "Pre-market" : marketStatus === "after" ? "After-hours" : "Previous close";
  const label = freshness === "delayed" && marketStatus && marketStatus !== "open" ? sessionLabel : s.label;
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${s.cls}`} title={marketStatus ? `Market ${marketStatus}; data freshness ${freshness}` : "Data freshness indicator"}>
      {label}
    </span>
  );
}

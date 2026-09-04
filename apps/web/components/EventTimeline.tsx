"use client";

import type { SymbolEvent } from "@/lib/types";

const SEV_DOT: Record<string, string> = {
  investigate: "bg-red-500",
  review: "bg-amber-500",
  notable: "bg-rose-500",
  background: "bg-gray-600",
};

export function EventTimeline({ events }: { events: SymbolEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-gray-500">No detected events yet.</p>;
  }
  return (
    <ol className="relative space-y-4 border-l border-gray-800 pl-4">
      {events.map((e) => (
        <li key={e.id}>
          <span className={`absolute -left-[7px] mt-1.5 h-3 w-3 rounded-full ${SEV_DOT[e.severity] ?? SEV_DOT.background}`} />
          <p className="text-sm font-medium">{e.title}</p>
          <p className="text-xs text-gray-400">{e.summary}</p>
          <p className="mt-0.5 text-[11px] text-gray-500">
            {new Date(e.detected_at).toLocaleString()} · score {e.final_score.toFixed(0)} · confidence{" "}
            {(e.confidence_score * 100).toFixed(0)}%
          </p>
          {e.evidence && <p className="mt-0.5 text-[11px] text-gray-500">Trigger: {e.evidence.trigger}</p>}
        </li>
      ))}
    </ol>
  );
}

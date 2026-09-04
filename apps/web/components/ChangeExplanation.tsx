"use client";

import type { AttentionCard } from "@/lib/types";

export function ChangeExplanation({ card }: { card: AttentionCard }) {
  const rel = card.evidence?.extra?.related_events ?? [];
  if (rel.length === 0) return null;
  return (
    <div className="rounded-lg border border-gray-800 bg-black/20 p-3 text-xs text-gray-400">
      <p className="mb-1 font-medium text-gray-300">Grouped signals for the same underlying movement:</p>
      <ul className="list-inside list-disc space-y-0.5">
        {rel.map((r, i) => (
          <li key={i}>
            {r.type.replace("_", " ")}: {r.title} (score {r.score.toFixed(0)})
          </li>
        ))}
      </ul>
    </div>
  );
}

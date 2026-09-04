"use client";

import type { AttentionCard as Card } from "@/lib/types";
import { AttentionCard } from "./AttentionCard";

export function AttentionFeed({ cards, compact = false }: { cards: Card[]; compact?: boolean }) {
  if (cards.length === 0) {
    return (
      <div className="card text-center text-sm text-gray-400">
        <div className="text-base text-slate-200">No meaningful changes detected.</div>
        <div className="mt-1">Your latest prices are shown above. 🎉</div>
      </div>
    );
  }
  return (
    <div className={compact ? "space-y-2" : "space-y-3"}>
      {cards.map((c) => (
        <div key={c.id} className={compact ? "[&_.summary-copy]:line-clamp-1 [&_.details-block]:hidden" : ""}>
          <AttentionCard card={c} />
        </div>
      ))}
    </div>
  );
}

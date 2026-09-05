"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { NotificationLogEntry } from "@/lib/types";

function timeAgo(iso: string): string {
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

const KIND_LABEL: Record<string, string> = {
  inapp: "In-app",
  webpush: "Push",
  email: "Email",
};

export function NotificationCenter() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);

  const log = useQuery({
    queryKey: ["notification-log"],
    queryFn: () => api.notificationLog(30),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const markRead = useMutation({
    mutationFn: (id: number) => api.markNotificationRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notification-log"] }),
  });

  const entries = log.data ?? [];
  const unread = entries.filter((e) => e.kind === "inapp" && !e.read_at).length;

  return (
    <div className="relative">
      <button
        className="shell-icon-button"
        aria-label={`Notifications${unread ? ` (${unread} unread)` : ""}`}
        onClick={() => setOpen((v) => !v)}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" />
        </svg>
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <>
          {/* click-away layer */}
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} aria-hidden="true" />
          <div className="absolute right-0 top-10 z-50 w-80 overflow-hidden rounded-xl border border-white/10 bg-[#101216] shadow-2xl shadow-black/50">
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-2.5">
              <span className="text-[11px] font-semibold tracking-wider text-gray-300">NOTIFICATIONS</span>
              {unread > 0 && (
                <button
                  className="text-[11px] text-emerald-300 hover:text-emerald-200"
                  onClick={() => {
                    for (const e of unreadIds(entries)) markRead.mutate(e);
                  }}
                >
                  Mark all read
                </button>
              )}
            </div>
            <div className="max-h-80 overflow-y-auto">
              {log.isLoading && <p className="px-4 py-6 text-center text-xs text-gray-500">Loading…</p>}
              {!log.isLoading && entries.length === 0 && (
                <p className="px-4 py-6 text-center text-xs text-gray-500">
                  Nothing yet. Alerts you trigger will show up here.
                </p>
              )}
              {entries.map((e) => (
                <NotificationRow key={e.id} entry={e} onRead={() => markRead.mutate(e.id)} />
              ))}
            </div>
            <Link
              href="/settings"
              onClick={() => setOpen(false)}
              className="block border-t border-white/10 px-4 py-2 text-center text-[11px] text-gray-400 hover:text-gray-200"
            >
              Notification settings →
            </Link>
          </div>
        </>
      )}
    </div>
  );
}

function unreadIds(entries: NotificationLogEntry[]): number[] {
  return entries.filter((e) => e.kind === "inapp" && !e.read_at).map((e) => e.id);
}

function NotificationRow({ entry, onRead }: { entry: NotificationLogEntry; onRead: () => void }) {
  const isUnread = entry.kind === "inapp" && !entry.read_at;
  return (
    <button
      className={`block w-full px-4 py-2.5 text-left transition-colors hover:bg-white/5 ${isUnread ? "bg-white/[0.04]" : ""}`}
      onClick={() => { if (isUnread) onRead(); }}
      title={isUnread ? "Mark as read" : undefined}
    >
      <div className="flex items-center gap-2">
        {isUnread && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />}
        <span className={`truncate text-xs ${isUnread ? "font-semibold text-gray-100" : "text-gray-300"}`}>
          {entry.title}
        </span>
        <span className="ml-auto shrink-0 text-[10px] text-gray-500">
          {KIND_LABEL[entry.kind] ?? entry.kind}
        </span>
      </div>
      <p className="mt-0.5 line-clamp-2 text-[11px] leading-snug text-gray-500">{entry.body}</p>
      <div className="mt-0.5 flex items-center gap-2 text-[10px] text-gray-600">
        <span>{timeAgo(entry.created_at)}</span>
        <span className={`uppercase ${entry.status === "delivered" ? "text-emerald-600" : entry.status === "failed" ? "text-rose-600" : "text-gray-600"}`}>
          {entry.status}
        </span>
      </div>
    </button>
  );
}

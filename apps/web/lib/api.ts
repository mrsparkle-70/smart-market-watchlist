"use client";

import type {
  AttentionFeed,
  Candle,
  NewsItem,
  NotificationChannel,
  NotificationLogEntry,
  NotificationPreferences,
  Preferences,
  Quote,
  RelativeResponse,
  Scenario,
  SimulateResult,
  SymbolEvent,
  Watchlist,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      ...init,
    });
  } catch (error) {
    const reason = error instanceof Error ? error.message : "network request failed";
    throw new Error(`API unavailable for ${path}: ${reason}`);
  }
  if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/api/auth")) {
    window.location.href = "/login";
    throw new Error("Not authenticated");
  }
  if (!res.ok) {
    let detail = res.statusText || "Request failed";
    try {
      const contentType = res.headers.get("content-type") ?? "";
      if (contentType.includes("application/json")) {
        const body = await res.json();
        detail = body.detail ?? JSON.stringify(body);
      } else {
        const text = await res.text();
        if (text.trim()) detail = text.slice(0, 240);
      }
    } catch {}
    throw new Error(`${init?.method ?? "GET"} ${path} failed (${res.status}): ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  health: () => request<{ status: string; provider: string }>("/api/health"),
  // auth
  register: (email: string, password: string) =>
    request("/api/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) =>
    request("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  me: () => request<{ id: number; email: string; last_visit_at: string | null }>("/api/auth/me"),
  // watchlists
  watchlists: () => request<Watchlist[]>("/api/watchlists"),
  createWatchlist: (name: string) =>
    request<Watchlist>("/api/watchlists", { method: "POST", body: JSON.stringify({ name }) }),
  renameWatchlist: (id: number, name: string) =>
    request<Watchlist>(`/api/watchlists/${id}`, { method: "PATCH", body: JSON.stringify({ name }) }),
  deleteWatchlist: (id: number) => request<void>(`/api/watchlists/${id}`, { method: "DELETE" }),
  addSymbol: (id: number, symbol: string, priority_tag = "normal") =>
    request(`/api/watchlists/${id}/symbols`, { method: "POST", body: JSON.stringify({ symbol, priority_tag }) }),
  updatePriority: (id: number, symbol: string, priority_tag: string) =>
    request(`/api/watchlists/${id}/symbols/${encodeURIComponent(symbol)}/priority`, { method: "PATCH", body: JSON.stringify({ priority_tag }) }),
  bulkAddSymbols: (id: number, symbols: string[], priority_tag = "normal") =>
    request<{ added: string[]; errors: { symbol: string; error: string }[] }>(`/api/watchlists/${id}/symbols/bulk`, { method: "POST", body: JSON.stringify({ symbols, priority_tag }) }),
  reorderSymbols: (id: number, symbols: string[]) =>
    request(`/api/watchlists/${id}/symbols/reorder`, { method: "PATCH", body: JSON.stringify({ symbols }) }),
  removeSymbol: (id: number, symbol: string) =>
    request<void>(`/api/watchlists/${id}/symbols/${symbol}`, { method: "DELETE" }),
  // market
  refreshWatchlist: (id: number) =>
    request(`/api/market/refresh-watchlist/${id}`, { method: "POST" }),
  latest: (symbol: string) => request<Quote>(`/api/market/${symbol}/latest`),
  searchSymbols: (query: string) => request<{ symbol: string; name: string; exchange: string; industry: string }[]>(`/api/market/search?q=${encodeURIComponent(query)}`),
  history: (symbol: string) => request<Candle[]>(`/api/market/${symbol}/history`),
  analytics: (symbol: string, days = 90) => request<import("./types").SymbolAnalytics>(`/api/market/${symbol}/analytics?days=${days}`),
  events: (symbol: string) => request<SymbolEvent[]>(`/api/market/${symbol}/events`),
  news: (symbol: string) => request<NewsItem[]>(`/api/market/${symbol}/news`),
  alerts: (symbol: string) => request<import("./types").PriceAlert[]>(`/api/market/${symbol}/alerts`),
  triggeredAlerts: (limit = 25) => request<import("./types").PriceAlert[]>(`/api/market/alerts/triggered?limit=${limit}`),
  createAlert: (symbol: string, condition: string, threshold: number) => request<import("./types").PriceAlert>(`/api/market/${symbol}/alerts`, { method: "POST", body: JSON.stringify({ condition, threshold }) }),
  deleteAlert: (symbol: string, id: number) => request<void>(`/api/market/${symbol}/alerts/${id}`, { method: "DELETE" }),
  portfolio: () => request<import("./types").PortfolioSummary>("/api/portfolio"),
  saveHolding: (symbol: string, quantity: number, average_cost: number) => request<import("./types").PortfolioHolding>(`/api/portfolio/${encodeURIComponent(symbol)}`, { method: "PUT", body: JSON.stringify({ symbol, quantity, average_cost }) }),
  deleteHolding: (symbol: string) => request<void>(`/api/portfolio/${encodeURIComponent(symbol)}`, { method: "DELETE" }),
  note: (symbol: string) => request<{ symbol: string; body: string; updated_at: string | null }>(`/api/market/${symbol}/note`),
  saveNote: (symbol: string, body: string) => request<{ symbol: string; body: string; updated_at: string | null }>(`/api/market/${symbol}/note`, { method: "PUT", body: JSON.stringify({ body }) }),
  // demo scenario library
  scenarios: () => request<Scenario[]>("/api/demo/scenarios"),
  demoSimulate: (scenario: string) =>
    request<SimulateResult>("/api/demo/simulate", { method: "POST", body: JSON.stringify({ scenario }) }),
  // attention feed + event state
  feed: (watchlistId?: number) =>
    request<AttentionFeed>(`/api/attention-feed${watchlistId ? `?watchlist_id=${watchlistId}` : ""}`),
  eventState: (eventId: number, action: "seen" | "reviewed" | "dismiss" | "save") =>
    request(`/api/events/${eventId}/${action}`, { method: "POST" }),
  visit: () =>
    request<{ previous_visit_at: string | null; recorded_visit_at: string }>(
      "/api/sessions/visit",
      { method: "POST" }
    ),
  preferences: () => request<Preferences>("/api/preferences"),
  updatePreferences: (p: Partial<Preferences>) =>
    request("/api/preferences", { method: "PATCH", body: JSON.stringify(p) }),
  // notifications (feature #1)
  notificationChannels: () => request<NotificationChannel[]>("/api/notifications/channels"),
  addEmailChannel: (email: string) =>
    request<NotificationChannel>("/api/notifications/channels/email", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  addWebPushChannel: (endpoint: string, keys: { p256dh: string; auth: string }) =>
    request<NotificationChannel>("/api/notifications/channels/webpush", {
      method: "POST",
      body: JSON.stringify({ endpoint, keys }),
    }),
  toggleChannel: (id: number, enabled: boolean) =>
    request<NotificationChannel>(`/api/notifications/channels/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ enabled }),
    }),
  removeChannel: (id: number) =>
    request<void>(`/api/notifications/channels/${id}`, { method: "DELETE" }),
  testChannel: (id: number) =>
    request<{ queued_log_id: number; delivered_in_this_call: number }>(
      `/api/notifications/channels/${id}/test`,
      { method: "POST" }
    ),
  notificationLog: (limit = 50) =>
    request<NotificationLogEntry[]>(`/api/notifications/log?limit=${limit}`),
  markNotificationRead: (id: number) =>
    request<void>(`/api/notifications/log/${id}/read`, { method: "POST" }),
  notificationPreferences: () =>
    request<NotificationPreferences>("/api/notifications/preferences"),
  updateNotificationPreferences: (p: Partial<NotificationPreferences>) =>
    request<NotificationPreferences>("/api/notifications/preferences", {
      method: "PATCH",
      body: JSON.stringify(p),
    }),
  vapidPublicKey: () => request<{ publicKey: string }>("/api/notifications/vapid-public-key"),
  // relative performance vs benchmark (feature #6)
  relative: (symbol: string, days = 90) =>
    request<RelativeResponse>(`/api/market/${symbol}/relative?days=${days}`),
};

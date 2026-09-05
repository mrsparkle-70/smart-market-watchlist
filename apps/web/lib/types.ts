export interface WatchlistSymbol {
  symbol: string;
  display_name: string;
  exchange: string;
  asset_type: string;
  sort_order: number;
  priority_tag: string;
}

export interface Watchlist {
  id: number;
  name: string;
  is_default: boolean;
  symbols: WatchlistSymbol[];
}

export interface EventEvidence {
  trigger: string;
  baseline: string;
  current: string;
  window: string;
  source: string;
  confidence: number;
  extra?: { related_events?: { type: string; title: string; score: number }[] };
}

export interface AttentionCard {
  id: number;
  symbol: string;
  company_name: string;
  event_type: string;
  title: string;
  summary: string;
  attention_score: number;
  confidence_score: number;
  final_score: number;
  severity: string;
  detected_at: string;
  price: number | null;
  change_since_last_visit_pct: number | null;
  change_since_close_pct: number | null;
  freshness: string;
  evidence: EventEvidence | null;
  user_state: {
    seen_at: string | null;
    reviewed_at: string | null;
    dismissed_at: string | null;
    saved_at: string | null;
  };
}

export interface FeedSummary {
  total_symbols: number;
  meaningful_changes: number;
  stale_instruments: number;
  biggest_positive_move: { symbol: string; change_pct: number } | null;
  biggest_negative_move: { symbol: string; change_pct: number } | null;
}

export interface AttentionFeed {
  since: string | null;
  generated_at: string;
  cards: AttentionCard[];
  summary: FeedSummary;
  change_brief: string;
}

export interface Quote {
  symbol: string;
  price: number;
  previous_close: number;
  open_price: number | null;
  high_price: number | null;
  low_price: number | null;
  volume: number | null;
  market_status: string;
  change_since_close_pct: number | null;
  freshness: string;
  data_quality: string;
  source_timestamp: string | null;
  captured_at: string;
  provider: string;
}

export interface Candle {
  ts: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number;
  volume: number | null;
}

export interface SymbolAnalytics {
  symbol: string;
  observations: number;
  first_price: number | null;
  last_price: number | null;
  return_pct: number | null;
  high: number | null;
  low: number | null;
  max_drawdown_pct: number | null;
  positive_observations: number;
  negative_observations: number;
  window_days: number;
}

export interface SymbolEvent {
  id: number;
  event_type: string;
  title: string;
  summary: string;
  attention_score: number;
  confidence_score: number;
  final_score: number;
  severity: string;
  detected_at: string;
  evidence: EventEvidence;
}

export interface Preferences {
  price_threshold: number;
  volume_threshold: number;
  volatility_threshold: number;
  notification_enabled: boolean;
  timezone: string;
}

export interface Scenario {
  id: string;
  name: string;
  description: string;
}

export interface NewsItem {
  headline: string;
  source: string;
  url: string;
  published_at: string | null;
  relevance_score: number;
  sentiment_label: string;
}

export interface PriceAlert {
  id: number;
  symbol: string;
  condition: "price_above" | "price_below" | "move_up" | "move_down";
  threshold: number;
  enabled: boolean;
  created_at: string;
  last_triggered_at: string | null;
  last_triggered_value: number | null;
}

export interface PortfolioHolding {
  id: number;
  symbol: string;
  quantity: number;
  average_cost: number;
  current_price: number | null;
  invested_value: number;
  market_value: number | null;
  unrealized_gain: number | null;
  updated_at: string;
  data_quality: string;
}

export interface PortfolioSummary {
  items: PortfolioHolding[];
  invested_value: number;
  market_value: number;
  unrealized_gain: number;
  priced_items: number;
}

export interface SimulateResult {
  scenario: string;
  baseline_just_built: boolean;
  applied: string[];
  pipeline: Record<string, number | string>;
}

export interface NotificationChannel {
  id: number;
  kind: "email" | "webpush";
  target: string;
  enabled: boolean;
  verified: boolean;
  last_used_at: string | null;
  created_at: string;
}

export interface NotificationLogEntry {
  id: number;
  kind: string;
  title: string;
  body: string;
  status: string;
  error: string;
  created_at: string;
  sent_at: string | null;
  read_at: string | null;
}

export interface NotificationPreferences {
  notification_enabled: boolean;
  daily_digest: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  timezone: string;
}

# Smart Market Watchlist — 100-feature product roadmap

This roadmap is ordered around the user's daily loop: discover → organize → understand → act → review. Features marked **now** are the first implementation batch; the remaining items are the durable backlog for the goal.

## Discover and onboarding

1. **now** Guided first-run onboarding.
2. **now** Empty-watchlist checklist.
3. **now** Symbol search with provider-backed suggestions.
4. Popular-symbol starter packs.
5. Import symbols from CSV.
6. Import from a broker export.
7. Import from a pasted list.
8. Symbol aliases and exchange-aware lookup.
9. Duplicate and invalid-symbol warnings.
10. Explain what “meaningful change” means.

## Watchlist organization

11. **now** Multiple named watchlists.
12. **now** Rename watchlists.
13. Reorder watchlists.
14. Drag-and-drop symbol ordering.
15. Symbol pinning.
16. Personal priority tags.
17. User-defined groups and folders.
18. Notes per symbol.
19. Color labels per symbol.
20. Archive a symbol without deleting history.

## Market monitoring

21. **now** Latest quote snapshot.
22. **now** Data freshness and market-session labels.
23. **now** Manual refresh.
24. **now** Optional five-minute auto-refresh.
25. Market open/close countdown.
26. Pre-market and after-hours prices.
27. Extended-hours toggle.
28. Market-wide breadth summary.
29. Index and sector benchmark comparison.
30. Multiple currencies and locale formatting.

## Understanding change

31. **now** Since-last-visit change brief.
32. **now** Attention score with evidence.
33. **now** Grouped corroborating signals.
34. **now** Severity tiers.
35. **now** Search and sort attention feed.
36. **now** Saved-only filter.
37. **now** Hide-reviewed filter.
38. **now** Compact feed mode.
39. Compare against a custom date range.
40. Compare against a chosen benchmark.

## Charts and analytics

41. Price history chart.
42. Duplicate-safe chart ingestion.
43. Volume chart.
44. Candlestick chart.
45. Moving-average overlays.
46. Relative-performance chart.
47. Drawdown chart.
48. Volatility chart.
49. Intraday chart when provider permits.
50. Chart range selector.

## Events and news

51. Corporate-event timeline.
52. Earnings calendar.
53. Earnings surprise history.
54. Dividend and split history.
55. Analyst-action timeline.
56. **now** Scored company news.
57. News source links.
58. News sentiment explanation.
59. News deduplication.
60. User-configurable event-type filters.

## Alerts and actions

61. **now** Mark reviewed.
62. **now** Dismiss an event.
63. **now** Save an event.
64. Price threshold alerts.
65. Volume-spike alerts.
66. Volatility alerts.
67. Crosses-moving-average alerts.
68. News-keyword alerts.
69. Earnings reminders.
70. Alert quiet hours.

## Personalization

71. **now** Persisted alert thresholds.
72. Per-symbol thresholds.
73. Sector preferences.
74. Risk-tolerance profile.
75. Investment horizon profile.
76. Configurable attention weights.
77. Timezone preference.
78. Currency preference.
79. Light accessibility theme.
80. Reduced-motion preference.

## Review and sharing

81. **now** CSV export of filtered changes.
82. Daily email digest.
83. Browser notifications.
84. Slack or webhook notifications.
85. Shareable read-only watchlist link.
86. Export a daily change report.
87. Weekly change retrospective.
88. Personal decision journal.
89. “What changed since Monday?” view.
90. Read/unread inbox for events.

## Reliability, trust, and scale

91. **now** Provider error and retry states.
92. Provider fallback chain.
93. Quote-vs-history quality indicators.
94. Conflicting-provider comparison.
95. Provider outage banner.
96. Backfill status indicator.
97. Request deduplication and rate-limit protection.
98. Background job monitoring.
99. Postgres production profile and migrations.
100. Audit log and account data export/deletion.

## Implementation order

The first build batches prioritize onboarding, quote visibility, change comprehension, alerts, and trust. Every batch must leave the app buildable, keep provider failures visible, and add tests for persistence and ownership boundaries before moving on.

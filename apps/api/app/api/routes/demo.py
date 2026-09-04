"""Demo storyline endpoints (section 23) — now a full scenario library.

Not part of the production contract — exists so the demo can show the
'since your last visit' experience without waiting for real market movement.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_market_provider
from app.core.config import settings
from app.core.database import get_db
from app.models import User, Watchlist, WatchlistSymbol
from app.providers.base import MarketDataProvider
from app.services.features import pct_change
from app.services.ingest import get_last_snapshot, ingest_symbol, ingest_watchlist

router = APIRouter(prefix="/api/demo", tags=["demo"])

# Scenario step kinds: shock | gap | corp | news | macross | tag
SCENARIOS: dict[str, dict] = {
    "earnings_beat": {
        "name": "Earnings beat",
        "description": "NVDA surges on heavy volume while MSFT reports an earnings surprise.",
        "steps": [
            ("shock", "NVDA", {"pct": 5.8, "volume_multiplier": 2.3}),
            ("corp", "MSFT", {"event_type": "earnings_surprise", "title": "Q3 earnings: revenue beat, guidance raised"}),
        ],
    },
    "flash_crash": {
        "name": "Flash crash",
        "description": "TSLA plunges hard on 5x volume; volatility and volume alarms everywhere.",
        "steps": [
            ("shock", "TSLA", {"pct": -8.5, "volume_multiplier": 5.0}),
            ("shock", "NVDA", {"pct": -1.2, "volume_multiplier": 1.5}),
        ],
    },
    "earnings_miss": {
        "name": "Earnings miss + guidance cut",
        "description": "NVDA gaps down on results; TSLA guidance gets cut.",
        "steps": [
            ("shock", "NVDA", {"pct": -6.2, "volume_multiplier": 3.1}),
            ("corp", "TSLA", {"event_type": "guidance_change", "title": "Guidance cut: deliveries outlook lowered"}),
        ],
    },
    "sector_rotation": {
        "name": "Sector rotation",
        "description": "NVDA rises +1.2% while the market (SPY) falls -1% — strength is relative.",
        "steps": [
            ("shock", "SPY", {"pct": -1.0, "volume_multiplier": 1.0}),
            ("shock", "NVDA", {"pct": 1.2, "volume_multiplier": 1.1}),
        ],
    },
    "trend_break": {
        "name": "Trend break",
        "description": "NVDA breaks below its 20-day moving average on rising volume.",
        "steps": [("macross", "NVDA", {"direction": "below"})],
    },
    "gap_up": {
        "name": "Gap up at open",
        "description": "NVDA opens +2.8% above its previous close.",
        "steps": [("gap", "NVDA", {"pct": 2.8})],
    },
    "news_burst": {
        "name": "News burst",
        "description": "Headlines hit AAPL, NVDA and MSFT — scored by relevance, not noise.",
        "steps": [
            ("news", "AAPL", {"headline": "Apple upgraded to Strong Buy as services revenue hits record", "source": "Reuters"}),
            ("news", "NVDA", {"headline": "NVIDIA faces antitrust probe over AI chip sales", "source": "Bloomberg"}),
            ("news", "MSFT", {"headline": "Microsoft announces $60B buyback and dividend raise", "source": "WSJ"}),
        ],
    },
    "corporate_actions": {
        "name": "Corporate actions",
        "description": "A dividend raise, a stock split and an analyst downgrade land at once.",
        "steps": [
            ("corp", "AAPL", {"event_type": "dividend_change", "title": "Dividend raised 8% to $0.26/quarter"}),
            ("corp", "TSLA", {"event_type": "stock_split", "title": "3-for-1 stock split announced"}),
            ("corp", "NVDA", {"event_type": "analyst_change", "title": "Downgraded to Neutral on valuation"}),
        ],
    },
    "personal_alert": {
        "name": "Personal watch alert",
        "description": "AAPL (tagged high-priority) moves just +2% — below the standard bar, above yours.",
        "steps": [
            ("tag", "AAPL", {"priority_tag": "high_priority"}),
            ("shock", "AAPL", {"pct": 2.0, "volume_multiplier": 1.2}),
        ],
    },
    "quiet_day": {
        "name": "Quiet day",
        "description": "Everything drifts. The feed should stay empty — that is the product working.",
        "steps": [],
    },
}



@router.get("/scenarios")
def list_scenarios():
    return [{"id": sid, "name": s["name"], "description": s["description"]} for sid, s in SCENARIOS.items()]


class SimulateBody(BaseModel):
    scenario: str = "earnings_beat"


@router.post("/simulate")
async def simulate(body: SimulateBody, user: User = Depends(get_current_user), db: Session = Depends(get_db),
                   provider: MarketDataProvider = Depends(get_market_provider)):
    """Baseline first (if missing), apply the scenario, run a pipeline pass."""
    if body.scenario not in SCENARIOS:
        raise HTTPException(status_code=422, detail=f"Unknown scenario: {body.scenario}")
    required_demo_methods = ("apply_shock", "set_gap", "add_corporate_event", "add_news", "force_ma_cross")
    if not all(hasattr(provider, method) for method in required_demo_methods):
        raise HTTPException(
            status_code=400,
            detail="Demo scenarios require MARKET_DATA_PROVIDER=mock. Use Refresh market data with the live provider.",
        )
    scenario = SCENARIOS[body.scenario]

    watchlists = list(db.execute(select(Watchlist).where(Watchlist.user_id == user.id)).scalars())
    if not watchlists:
        raise HTTPException(status_code=400, detail="Create a watchlist with symbols first")
    wl_ids = [w.id for w in watchlists]

    symbol_rows = db.execute(
        select(WatchlistSymbol.symbol).where(WatchlistSymbol.watchlist_id.in_(wl_ids))
    ).scalars().all()
    symbols = set(symbol_rows)
    if not symbols:
        raise HTTPException(status_code=400, detail="Add symbols to your watchlist first")

    # 1) Ensure a baseline snapshot exists for every symbol (events need a 'since')
    baseline_just_built = False
    from app.models import MarketSnapshot
    from sqlalchemy import func

    snap_count = db.execute(
        select(func.count()).select_from(MarketSnapshot).where(MarketSnapshot.symbol.in_(symbols))
    ).scalar_one()
    if snap_count == 0:
        # Include the benchmark (SPY) so market-relative returns have a baseline too
        baseline_symbols = sorted(set(symbols) | {settings.BENCHMARK_SYMBOL.upper()})
        for sym in baseline_symbols:
            await ingest_symbol(db, provider, sym)
        baseline_just_built = True

    # 2) Apply scenario steps (skipping symbols the user doesn't watch)
    applied: list[str] = []
    for kind, sym, args in scenario["steps"]:
        if sym not in symbols and not (kind == "shock" and sym == "SPY"):
            continue
        if kind == "shock":
            provider.apply_shock(sym, **args)
            applied.append(f"{sym} {args['pct']:+.1f}% on {args.get('volume_multiplier', 1)}x volume")
        elif kind == "gap":
            provider.set_gap(sym, **args)
            applied.append(f"{sym} opens {args['pct']:+.1f}% gap")
        elif kind == "corp":
            provider.add_corporate_event(sym, args["event_type"], args["title"])
            applied.append(f"{sym}: {args['title']}")
        elif kind == "news":
            from datetime import datetime, timezone

            from app.providers.base import NewsArticle

            provider.add_news(NewsArticle(
                symbol=sym, headline=args["headline"], source=args["source"],
                url="https://example.com/news", published_at=datetime.now(timezone.utc),
            ))
            applied.append(f"{sym}: news — {args['headline'][:50]}…")
        elif kind == "macross":
            provider.force_ma_cross(sym, **args)
            applied.append(f"{sym} crosses {'above' if args['direction'] == 'above' else 'below'} 20d MA")
        elif kind == "tag":
            ws = db.execute(select(WatchlistSymbol).where(
                WatchlistSymbol.watchlist_id.in_(wl_ids), WatchlistSymbol.symbol == sym
            ).limit(1)).scalars().first()
            if ws:
                ws.priority_tag = args["priority_tag"]
                db.commit()
                applied.append(f"{sym} tagged {args['priority_tag']}")

    # 3) Pipeline pass over the user's watchlists.
    # Compute the benchmark delta ONCE so all watchlists share the same baseline
    # (otherwise an empty first watchlist would advance the SPY snapshot first).
    bench_ret = None
    bsym = settings.BENCHMARK_SYMBOL
    prev_bench = get_last_snapshot(db, bsym.upper())
    bq = await provider.get_quote(bsym)
    if prev_bench is not None and prev_bench.price:
        bench_ret = pct_change(bq.price, prev_bench.price)
    if bench_ret is None:
        await ingest_symbol(db, provider, bsym)  # seed SPY baseline for next cycle
    else:
        await ingest_symbol(db, provider, bsym)  # advance its snapshot in step

    results = {}
    for wl_id in wl_ids:
        results.update(await ingest_watchlist(db, provider, wl_id, benchmark_return=bench_ret))

    return {"scenario": body.scenario, "baseline_just_built": baseline_just_built,
            "applied": applied, "pipeline": results,
            "note": "Reload the feed — it reflects what changed since your last visit."}

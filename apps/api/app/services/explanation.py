"""Explanation service (section 9). Deterministic templates first.

An optional LLM may REWRITE verified facts into friendlier language, but receives
only structured facts and may never invent causes or advice (section 15).
"""
from __future__ import annotations

import json
from typing import Any

from app.core.config import settings

PCT = "{:+.1f}%"
X = "{:.1f}x"
PP = "{:+.1f} pct-pts"


def explain_event(symbol: str, *, change_since_visit: float | None, volume_ratio_value: float | None,
                  relative_return: float | None, event_type: str, event_title: str = "") -> str:
    """Deterministic, fact-only explanation used on attention cards."""
    parts: list[str] = []
    if change_since_visit is not None and abs(change_since_visit) > 0.05:
        direction = "up" if change_since_visit > 0 else "down"
        parts.append(f"{symbol} is {direction} {PCT.format(abs(change_since_visit))} since your last visit.")
    if volume_ratio_value is not None and volume_ratio_value >= 1.5:
        parts.append(f"Trading volume is {X.format(volume_ratio_value)} its recent average.")
    if relative_return is not None and abs(relative_return) >= 1.0:
        rel = "outperforming" if relative_return > 0 else "underperforming"
        parts.append(f"The stock is {rel} its benchmark by {PP.format(relative_return)}.")
    if event_type in ("earnings", "earnings_surprise", "guidance_change", "dividend_change",
                      "stock_split", "merger_acquisition", "analyst_change"):
        parts.append(event_title or "A corporate event was detected.")
    if not parts:
        parts.append(f"{symbol}: no significant change since your last visit.")
    return " ".join(parts)


def explain_group(symbol: str, group_events: list[dict[str, Any]]) -> str:
    """Noise control (section 14): one narrative for grouped related events."""
    change = next((e["change_since_visit"] for e in group_events if e.get("change_since_visit") is not None), None)
    vol = next((e["volume_ratio"] for e in group_events if e.get("volume_ratio") is not None), None)
    rel = next((e["relative_return"] for e in group_events if e.get("relative_return") is not None), None)
    return explain_event(symbol, change_since_visit=change, volume_ratio_value=vol,
                         relative_return=rel, event_type="group")


# ---- Optional LLM rewrite (facts in, validated JSON out) --------------------

SYSTEM_PROMPT = (
    "You are a financial data summarizer. Rewrite the verified facts below into a "
    "concise explanation of what changed. Do not invent causes. Do not predict prices. "
    "Do not give buy, sell, or hold advice. Return JSON: "
    '{"summary": "string", "key_facts": ["string"], "risk_note": "string"}'
)


async def maybe_llm_rewrite(facts: dict[str, Any]) -> dict[str, Any] | None:
    """Rewrite verified facts via a free-tier LLM (Groq/OpenAI-compatible).

    Returns None whenever the LLM is unconfigured, fails, or returns invalid
    output — the deterministic template always remains the fallback.
    """
    if not settings.LLM_API_KEY:
        return None
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(facts, default=str)},
            ],
        )
        raw = response.choices[0].message.content or ""
        data = json.loads(raw)
        summary = str(data.get("summary", "")).strip()
        if not summary:
            return None
        # Guardrail: strip anything resembling advice if a model misbehaves.
        forbidden = ("buy", "sell", "hold")
        if any(f" {w} " in f" {summary.lower()} " for w in forbidden) and "advice" in summary.lower():
            return None
        return {"summary": summary, "key_facts": data.get("key_facts", []), "risk_note": data.get("risk_note", "")}
    except Exception:
        return None  # fallback to deterministic template — the app works without the LLM

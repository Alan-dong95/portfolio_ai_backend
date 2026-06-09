"""Enrich matched feed items with AI summaries and impact assessments."""

from __future__ import annotations

from app.ai.impact_analyzer import assess_impact
from app.ai.llm_service import analyze_news
from app.config import settings
from app.schemas.feed import FeedItem


def _priority_for_impact(impact: str, relevance_score: int) -> str:
    if impact == "high" or relevance_score >= 90:
        return "high"
    if impact == "medium" or relevance_score >= 70:
        return "medium"
    return "low"


def enrich_feed_item(item: FeedItem, *, language: str = "en") -> FeedItem:
    intel = analyze_news(
        title=item.title,
        content=item.summary,
        holdings=item.related_holdings,
        relevance_score=item.relevance_score,
        language=language,
    )
    impact = intel.impact
    priority = _priority_for_impact(impact, item.relevance_score)
    why = intel.why_this_matters or item.why_this_matters
    ai_summary = intel.summary or item.summary

    return item.model_copy(
        update={
            "ai_summary": ai_summary,
            "why_this_matters": why,
            "impact": impact,
            "priority": priority,
            "ai_confidence": intel.confidence,
        }
    )


def enrich_feed_items(
    items: list[FeedItem],
    *,
    language: str = "en",
    max_llm_items: int | None = None,
) -> list[FeedItem]:
    """Enrich feed items; LLM calls are capped to control latency/cost."""
    if not items:
        return []

    limit = max_llm_items
    if limit is None:
        limit = 12 if settings.llm_enabled and _has_llm_credentials() else 0

    enriched: list[FeedItem] = []
    for index, item in enumerate(items):
        if index < limit:
            enriched.append(enrich_feed_item(item, language=language))
        else:
            enriched.append(_heuristic_enrich(item))
    return enriched


def _has_llm_credentials() -> bool:
    from app.ai.llm_service import _resolve_credentials

    return _resolve_credentials() is not None


def _heuristic_enrich(item: FeedItem) -> FeedItem:
    assessment = assess_impact(
        title=item.title,
        content=item.summary,
        relevance_score=item.relevance_score,
        related_holdings=item.related_holdings,
    )
    return item.model_copy(
        update={
            "ai_summary": item.summary,
            "impact": assessment.impact,
            "priority": _priority_for_impact(assessment.impact, item.relevance_score),
            "ai_confidence": assessment.confidence,
        }
    )

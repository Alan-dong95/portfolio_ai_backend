"""Impact assessment — heuristic today, LLM-enhanced via llm_service."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.feed import FeedItem


@dataclass(frozen=True)
class ImpactAssessment:
    impact: str
    confidence: int


_RISK_KEYWORDS = (
    "restriction",
    "export control",
    "sanction",
    "tariff",
    "rate hike",
    "inflation",
    "recession",
    "decline",
    "fall",
    "drop",
    "crash",
    "ban",
    "probe",
    "investigation",
    "lawsuit",
    "出口",
    "管制",
    "制裁",
    "关税",
    "加息",
    "通胀",
    "衰退",
    "下跌",
    "暴跌",
)

_OPPORTUNITY_KEYWORDS = (
    "inflow",
    "record",
    "surge",
    "growth",
    "expansion",
    "launch",
    "approval",
    "beat",
    "upgrade",
    "investment",
    "spending",
    "demand",
    "流入",
    "创纪录",
    "增长",
    "扩张",
    "发布",
    "获批",
    "超预期",
    "上调",
    "需求",
)


def assess_impact(
    *,
    title: str,
    content: str,
    relevance_score: int,
    related_holdings: list[str],
) -> ImpactAssessment:
    text = f"{title} {content}".lower()
    base_confidence = max(60, min(98, relevance_score - 2))

    if relevance_score >= 90:
        impact = "high"
    elif relevance_score >= 70:
        impact = "medium"
    else:
        impact = "low"

    if related_holdings and relevance_score >= 85:
        base_confidence = min(98, base_confidence + 3)

    return ImpactAssessment(impact=impact, confidence=base_confidence)


def is_risk_signal(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    return any(kw in text for kw in _RISK_KEYWORDS)


def is_opportunity_signal(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    return any(kw in text for kw in _OPPORTUNITY_KEYWORDS)


def extract_risk_phrase(item: FeedItem) -> str | None:
    if not is_risk_signal(item.title, item.summary):
        return None
    return _shorten_headline(item.title)


def extract_opportunity_phrase(item: FeedItem) -> str | None:
    if not is_opportunity_signal(item.title, item.summary):
        return None
    return _shorten_headline(item.title)


def _shorten_headline(title: str, max_len: int = 56) -> str:
    cleaned = title.strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1].rstrip() + "…"

"""Morning brief synthesis — rule-based today, LLM-ready."""

from __future__ import annotations

from app.ai.impact_analyzer import (
    extract_opportunity_phrase,
    extract_risk_phrase,
    is_opportunity_signal,
    is_risk_signal,
)
from app.schemas.brief import MorningBriefResponse
from app.schemas.feed import FeedItem
from app.services.news_service import _profile_for, _label_for


_CATEGORY_LABELS_EN: dict[str, str] = {
    "semiconductor": "Semiconductor",
    "digital_assets": "Digital Assets",
    "technology": "AI & Technology",
    "macro": "Macro",
}

_CATEGORY_LABELS_ZH: dict[str, str] = {
    "semiconductor": "半导体",
    "digital_assets": "数字资产",
    "technology": "AI 与科技",
    "macro": "宏观",
}


def _sector_labels(symbols: list[str], *, language: str) -> list[str]:
    labels: dict[str, int] = {}
    for symbol in symbols:
        profile = _profile_for(symbol)
        category = profile.get("category", "macro")
        label_map = _CATEGORY_LABELS_ZH if language == "zh" else _CATEGORY_LABELS_EN
        label = label_map.get(category, _label_for(profile, language=language))
        labels[label] = labels.get(label, 0) + 1
    ranked = sorted(labels.items(), key=lambda x: x[1], reverse=True)
    return [name for name, _ in ranked[:3]]


def _headline(high_count: int, *, language: str) -> str:
    if language == "zh":
        if high_count == 0:
            return "今日暂无高影响事件"
        return f"今日 {high_count} 个高影响事件"
    if high_count == 0:
        return "No high impact events today"
    if high_count == 1:
        return "1 high impact event today"
    return f"{high_count} high impact events today"


def _summary(sectors: list[str], *, language: str) -> str:
    if not sectors:
        if language == "zh":
            return "添加持仓后，我们将为您识别最重要的市场信号。"
        return "Add holdings to surface what matters most to your portfolio."

    joined = "、".join(sectors) if language == "zh" else ", ".join(sectors)
    if language == "zh":
        return f"您的组合主要暴露在 {joined} 等领域。"
    return f"Your portfolio is most exposed to {joined}."


def _fallback_risks(items: list[FeedItem], *, language: str) -> list[str]:
    risks: list[str] = []
    for item in items:
        phrase = extract_risk_phrase(item)
        if phrase:
            risks.append(phrase)
        if len(risks) >= 3:
            break
    if risks:
        return risks[:3]
    defaults_en = ["US yields continue rising", "Semiconductor export restrictions"]
    defaults_zh = ["美债收益率持续上行", "半导体出口限制趋严"]
    return defaults_zh if language == "zh" else defaults_en


def _fallback_opportunities(items: list[FeedItem], *, language: str) -> list[str]:
    opps: list[str] = []
    for item in items:
        phrase = extract_opportunity_phrase(item)
        if phrase:
            opps.append(phrase)
        if len(opps) >= 3:
            break
    if opps:
        return opps[:3]
    defaults_en = ["AI infrastructure spending", "Bitcoin ETF inflows"]
    defaults_zh = ["AI 基础设施投入", "比特币 ETF 资金流入"]
    return defaults_zh if language == "zh" else defaults_en


def generate_brief(
    items: list[FeedItem],
    symbols: list[str],
    *,
    language: str = "en",
) -> MorningBriefResponse:
    lang = "zh" if language.lower().startswith("zh") else "en"
    high_items = [i for i in items if i.priority == "high" or i.impact == "high"]
    high_count = len(high_items)

    exposure_symbols = symbols or [
        h for item in items for h in item.related_holdings
    ]
    sectors = _sector_labels(exposure_symbols, language=lang)

    risk_candidates = [
        extract_risk_phrase(i) or i.title
        for i in items
        if is_risk_signal(i.title, i.ai_summary or i.summary)
    ]
    opp_candidates = [
        extract_opportunity_phrase(i) or i.title
        for i in items
        if is_opportunity_signal(i.title, i.ai_summary or i.summary)
    ]

    top_risks = _dedupe_preserve(risk_candidates)[:3] or _fallback_risks(items, language=lang)
    top_opportunities = _dedupe_preserve(opp_candidates)[:3] or _fallback_opportunities(
        items, language=lang
    )

    return MorningBriefResponse(
        headline=_headline(high_count, language=lang),
        summary=_summary(sectors, language=lang),
        top_risks=top_risks,
        top_opportunities=top_opportunities,
        high_impact_count=high_count,
        exposure_sectors=sectors,
    )


def _dedupe_preserve(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value.strip())
    return result

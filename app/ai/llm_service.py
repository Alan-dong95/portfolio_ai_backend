"""LLM integration layer — OpenAI, DeepSeek, with heuristic fallback."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.services.cache_service import summary_cache

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NewsIntel:
    summary: str
    why_this_matters: str
    impact: str
    confidence: int


def _cache_key(title: str, content: str, holdings: list[str], language: str) -> str:
    payload = f"{title}|{content}|{','.join(sorted(holdings))}|{language}"
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def _default_model() -> str:
    if settings.llm_model:
        return settings.llm_model
    if settings.llm_provider == "deepseek":
        return "deepseek-v4-flash"
    return "gpt-4o-mini"


def _resolve_credentials() -> tuple[str, str] | None:
    provider = settings.llm_provider
    if provider == "deepseek" and settings.deepseek_api_key:
        return settings.deepseek_api_key, settings.deepseek_base_url
    if provider in {"openai", "deepseek"} and settings.openai_api_key:
        return settings.openai_api_key, settings.openai_base_url
    if settings.deepseek_api_key:
        return settings.deepseek_api_key, settings.deepseek_base_url
    if settings.openai_api_key:
        return settings.openai_api_key, settings.openai_base_url
    return None


def _heuristic_intel(
    *,
    title: str,
    content: str,
    holdings: list[str],
    relevance_score: int,
    language: str,
) -> NewsIntel:
    from app.ai.impact_analyzer import assess_impact

    assessment = assess_impact(
        title=title,
        content=content,
        relevance_score=relevance_score,
        related_holdings=holdings,
    )
    if language == "zh":
        ai_summary = _truncate(content or title, 120)
        if not ai_summary or ai_summary == title:
            ai_summary = f"{title}。"
        why = (
            f"您持有 {', '.join(holdings)}，该事件可能影响相关敞口。"
            if holdings
            else "该事件可能影响您组合的整体风险敞口。"
        )
    else:
        ai_summary = _truncate(content or title, 140)
        why = (
            f"You hold {', '.join(holdings)}. This event may affect related exposure."
            if holdings
            else "This event may affect your overall portfolio risk profile."
        )
    return NewsIntel(
        summary=ai_summary,
        why_this_matters=why,
        impact=assessment.impact,
        confidence=assessment.confidence,
    )


def _truncate(text: str, max_len: int) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1].rstrip() + "…"


def _parse_llm_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _call_chat_completion(system: str, user: str) -> str | None:
    creds = _resolve_credentials()
    if creds is None:
        return None
    api_key, base_url = creds
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": _default_model(),
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("LLM request failed: %s", exc)
        return None

    choices = data.get("choices") or []
    if not choices:
        return None
    message = choices[0].get("message") or {}
    content = message.get("content")
    return content if isinstance(content, str) else None


def analyze_news(
    *,
    title: str,
    content: str,
    holdings: list[str],
    relevance_score: int = 75,
    language: str = "en",
    use_cache: bool = True,
) -> NewsIntel:
    """Generate AI summary, why-it-matters, impact, and confidence for a news item."""
    lang = "zh" if language.lower().startswith("zh") else "en"
    key = _cache_key(title, content, holdings, lang)

    if use_cache:
        cached = summary_cache.get(key)
        if cached is not None:
            return NewsIntel(
                summary=cached["summary"],
                why_this_matters=cached["why_this_matters"],
                impact=cached["impact"],
                confidence=int(cached["confidence"]),
            )

    if not settings.llm_enabled:
        intel = _heuristic_intel(
            title=title,
            content=content,
            holdings=holdings,
            relevance_score=relevance_score,
            language=lang,
        )
        summary_cache.set(key, intel.__dict__)
        return intel

    holdings_text = ", ".join(holdings) if holdings else "none"
    if lang == "zh":
        system = (
            "你是投资组合情报分析师。根据新闻与持仓，输出 JSON："
            '{"summary":"1-2句中文摘要","why_this_matters":"为何对持仓重要",'
            '"impact":"high|medium|low","confidence":0-100整数}。'
            "不要聊天，只输出 JSON。"
        )
        user = (
            f"标题：{title}\n内容：{content}\n持仓：{holdings_text}\n"
            f"相关度：{relevance_score}"
        )
    else:
        system = (
            "You are a portfolio intelligence analyst. Return JSON only: "
            '{"summary":"1-2 sentence summary","why_this_matters":"portfolio relevance",'
            '"impact":"high|medium|low","confidence":0-100 integer}. '
            "No chat. JSON only."
        )
        user = (
            f"Title: {title}\nContent: {content}\nHoldings: {holdings_text}\n"
            f"Relevance: {relevance_score}"
        )

    raw = _call_chat_completion(system, user)
    if raw is None:
        intel = _heuristic_intel(
            title=title,
            content=content,
            holdings=holdings,
            relevance_score=relevance_score,
            language=lang,
        )
        summary_cache.set(key, intel.__dict__)
        return intel

    try:
        parsed = _parse_llm_json(raw)
        impact = str(parsed.get("impact", "medium")).lower()
        if impact not in {"high", "medium", "low"}:
            impact = "medium"
        confidence = int(parsed.get("confidence", relevance_score))
        confidence = max(60, min(98, confidence))
        intel = NewsIntel(
            summary=str(parsed.get("summary") or content or title),
            why_this_matters=str(parsed.get("why_this_matters") or ""),
            impact=impact,
            confidence=confidence,
        )
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("LLM JSON parse failed: %s", exc)
        intel = _heuristic_intel(
            title=title,
            content=content,
            holdings=holdings,
            relevance_score=relevance_score,
            language=lang,
        )

    summary_cache.set(key, intel.__dict__)
    return intel

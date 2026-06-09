from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.schemas.feed import FeedItem
from app.services.symbol_service import lookup_symbol

logger = logging.getLogger(__name__)

NEWS_API_BASE = "https://newsapi.org/v2"
CACHE_TTL_SECONDS = settings.news_cache_ttl_seconds
NEWS_API_KEY = settings.news_api_key

_SYMBOL_PROFILES: dict[str, dict[str, Any]] = {
    "NVDA": {
        "keywords": ["nvidia", "nvda"],
        "keywords_zh": ["英伟达", "nvidia", "nvda"],
        "secondary": ["ai gpu", "gpu", "artificial intelligence chip"],
        "secondary_zh": ["人工智能芯片", "gpu", "算力", "ai芯片"],
        "category": "semiconductor",
        "label": "NVIDIA",
        "label_zh": "英伟达",
    },
    "BTC": {
        "keywords": ["bitcoin", "btc"],
        "keywords_zh": ["比特币", "bitcoin", "btc"],
        "secondary": ["etf", "crypto", "cryptocurrency", "digital asset"],
        "secondary_zh": ["etf", "加密", "数字货币", "虚拟资产"],
        "category": "digital_assets",
        "label": "Bitcoin",
        "label_zh": "比特币",
    },
    "BTC-USD": {
        "keywords": ["bitcoin", "btc"],
        "keywords_zh": ["比特币", "bitcoin", "btc"],
        "secondary": ["etf", "crypto", "cryptocurrency", "digital asset"],
        "secondary_zh": ["etf", "加密", "数字货币", "虚拟资产"],
        "category": "digital_assets",
        "label": "Bitcoin",
        "label_zh": "比特币",
    },
    "TSM": {
        "keywords": ["tsmc", "taiwan semiconductor", "tsm"],
        "keywords_zh": ["台积电", "tsmc", "台湾半导体"],
        "secondary": ["chip", "foundry", "semiconductor"],
        "secondary_zh": ["芯片", "晶圆", "半导体", "代工"],
        "category": "semiconductor",
        "label": "TSMC",
        "label_zh": "台积电",
    },
    "301392": {
        "keywords": ["semiconductor", "chip", "export restriction", "china chip"],
        "keywords_zh": ["半导体", "芯片", "出口管制", "国产芯片", "301392"],
        "secondary": ["asml", "wafer", "fab"],
        "secondary_zh": ["光刻", "晶圆", "fab", "设备"],
        "category": "semiconductor",
        "label": "301392",
        "label_zh": "301392",
    },
    "AAPL": {
        "keywords": ["apple", "aapl", "iphone", "ipad"],
        "keywords_zh": ["苹果", "apple", "iphone", "ipad"],
        "secondary": ["tim cook", "app store"],
        "secondary_zh": ["库克", "app store", "ios"],
        "category": "technology",
        "label": "Apple",
        "label_zh": "苹果",
    },
    "MSFT": {
        "keywords": ["microsoft", "msft", "azure", "openai"],
        "keywords_zh": ["微软", "microsoft", "azure", "openai"],
        "secondary": ["cloud", "copilot"],
        "secondary_zh": ["云计算", "copilot", "azure"],
        "category": "technology",
        "label": "Microsoft",
        "label_zh": "微软",
    },
    "GOOGL": {
        "keywords": ["google", "alphabet", "googl", "gemini"],
        "keywords_zh": ["谷歌", "google", "alphabet", "gemini"],
        "secondary": ["search", "youtube", "cloud"],
        "secondary_zh": ["搜索", "youtube", "云计算"],
        "category": "technology",
        "label": "Alphabet",
        "label_zh": "谷歌",
    },
    "META": {
        "keywords": ["meta", "facebook", "instagram", "whatsapp"],
        "keywords_zh": ["meta", "facebook", "instagram", "脸书"],
        "secondary": ["zuckerberg", "social media"],
        "secondary_zh": ["扎克伯格", "社交媒体"],
        "category": "technology",
        "label": "Meta",
        "label_zh": "Meta",
    },
    "ETH": {
        "keywords": ["ethereum", "eth"],
        "keywords_zh": ["以太坊", "ethereum", "eth"],
        "secondary": ["crypto", "defi", "blockchain"],
        "secondary_zh": ["加密", "defi", "区块链"],
        "category": "digital_assets",
        "label": "Ethereum",
        "label_zh": "以太坊",
    },
    "ETH-USD": {
        "keywords": ["ethereum", "eth"],
        "keywords_zh": ["以太坊", "ethereum", "eth"],
        "secondary": ["crypto", "defi", "blockchain"],
        "secondary_zh": ["加密", "defi", "区块链"],
        "category": "digital_assets",
        "label": "Ethereum",
        "label_zh": "以太坊",
    },
}

_FALLBACK_ARTICLES: list[dict[str, Any]] = [
    {
        "source": {"name": "Reuters"},
        "title": "NVIDIA launches new AI GPU architecture for hyperscale data centers",
        "description": "NVIDIA unveiled its latest AI accelerator lineup, targeting record demand from cloud providers.",
        "url": "https://example.com/nvidia-ai-gpu",
        "publishedAt": "2026-06-09T08:30:00Z",
    },
    {
        "source": {"name": "Bloomberg"},
        "title": "Bitcoin ETF inflows hit record as institutional demand accelerates",
        "description": "Spot Bitcoin ETF products saw their largest weekly inflow since launch, lifting crypto sentiment.",
        "url": "https://example.com/bitcoin-etf-inflows",
        "publishedAt": "2026-06-09T07:15:00Z",
    },
    {
        "source": {"name": "Financial Times"},
        "title": "TSMC advanced packaging capacity remains tight amid AI chip orders",
        "description": "CoWoS load factors stay elevated as NVIDIA and hyperscalers expand AI infrastructure spending.",
        "url": "https://example.com/tsmc-packaging",
        "publishedAt": "2026-06-09T06:45:00Z",
    },
    {
        "source": {"name": "Caixin"},
        "title": "China chip export restrictions expand to additional equipment categories",
        "description": "New semiconductor export controls may affect domestic equipment makers and supply chains.",
        "url": "https://example.com/china-chip-export",
        "publishedAt": "2026-06-09T05:20:00Z",
    },
    {
        "source": {"name": "Wall Street Journal"},
        "title": "Fed officials signal patience as inflation data stabilizes",
        "description": "Macro policy expectations shift as markets weigh the path of rate cuts into the second half.",
        "url": "https://example.com/fed-inflation",
        "publishedAt": "2026-06-09T04:00:00Z",
    },
]

_FALLBACK_ARTICLES_ZH: list[dict[str, Any]] = [
    {
        "source": {"name": "财联社"},
        "title": "英伟达发布新一代 AI GPU，面向超大规模数据中心",
        "description": "英伟达推出最新 AI 加速器产品线，以满足云厂商创纪录的算力需求。",
        "url": "https://example.com/zh/nvidia-ai-gpu",
        "publishedAt": "2026-06-09T08:30:00Z",
    },
    {
        "source": {"name": "第一财经"},
        "title": "比特币 ETF 资金流入创纪录，机构需求持续升温",
        "description": "现货比特币 ETF 单周净流入创上线以来新高，带动加密市场情绪回暖。",
        "url": "https://example.com/zh/bitcoin-etf-inflows",
        "publishedAt": "2026-06-09T07:15:00Z",
    },
    {
        "source": {"name": "证券时报"},
        "title": "台积电先进封装产能仍紧张，AI 芯片订单持续高位",
        "description": "CoWoS 产能利用率维持高位，英伟达与云巨头继续加码 AI 基础设施投入。",
        "url": "https://example.com/zh/tsmc-packaging",
        "publishedAt": "2026-06-09T06:45:00Z",
    },
    {
        "source": {"name": "财新"},
        "title": "半导体出口管制范围扩大，部分设备材料审批趋严",
        "description": "新一轮芯片出口限制或影响国内设备厂商订单与产业链估值预期。",
        "url": "https://example.com/zh/china-chip-export",
        "publishedAt": "2026-06-09T05:20:00Z",
    },
    {
        "source": {"name": "新华社"},
        "title": "美联储官员暗示通胀趋稳，降息预期再受关注",
        "description": "宏观政策预期随通胀数据波动，市场关注下半年利率路径。",
        "url": "https://example.com/zh/fed-inflation",
        "publishedAt": "2026-06-09T04:00:00Z",
    },
]


@dataclass
class NewsArticle:
    id: str
    title: str
    summary: str
    source: str
    url: str
    published_at: datetime


@dataclass
class _NewsCache:
    fetched_at: datetime
    articles: list[NewsArticle]


_cache: dict[str, _NewsCache] = {}


def _normalize_language(language: str | None) -> str:
    if not language:
        return "en"
    code = language.strip().lower().replace("_", "-").split("-")[0]
    return "zh" if code == "zh" else "en"


def _normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def _profile_for(symbol: str) -> dict[str, Any]:
    key = _normalize_symbol(symbol)
    if key in _SYMBOL_PROFILES:
        return _SYMBOL_PROFILES[key]
    base = key.split("-")[0]
    if base in _SYMBOL_PROFILES:
        return _SYMBOL_PROFILES[base]
    return {
        "keywords": [key.lower(), base.lower()],
        "secondary": [],
        "category": "macro",
        "label": key,
        "label_zh": key,
    }


def _keywords_for(profile: dict[str, Any], language: str) -> list[str]:
    if language == "zh":
        return profile.get("keywords_zh") or profile.get("keywords", [])
    return profile.get("keywords", [])


def _secondary_for(profile: dict[str, Any], language: str) -> list[str]:
    if language == "zh":
        return profile.get("secondary_zh") or profile.get("secondary", [])
    return profile.get("secondary", [])


def _label_for(profile: dict[str, Any], language: str) -> str:
    if language == "zh":
        return profile.get("label_zh") or profile.get("label", "")
    return profile.get("label", "")


def _article_id(url: str, title: str) -> str:
    digest = hashlib.sha256(f"{url}|{title}".encode()).hexdigest()
    return digest[:16]


def _parse_published_at(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        normalized = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def _article_from_newsapi(raw: dict[str, Any]) -> NewsArticle | None:
    title = (raw.get("title") or "").strip()
    if not title or title == "[Removed]":
        return None

    url = (raw.get("url") or "").strip()
    description = (raw.get("description") or raw.get("content") or "").strip()
    if description.endswith("[+") and "chars]" in description:
        description = description.split("[+")[0].strip()

    source_obj = raw.get("source") or {}
    source_name = ""
    if isinstance(source_obj, dict):
        source_name = (source_obj.get("name") or "").strip()

    return NewsArticle(
        id=_article_id(url or title, title),
        title=title,
        summary=description or title,
        source=source_name,
        url=url,
        published_at=_parse_published_at(raw.get("publishedAt")),
    )


def _dedupe_articles(articles: list[NewsArticle]) -> list[NewsArticle]:
    seen: set[str] = set()
    unique: list[NewsArticle] = []
    for article in articles:
        if article.id in seen:
            continue
        seen.add(article.id)
        unique.append(article)
    return unique


def _fetch_newsapi(path: str, params: dict[str, Any]) -> list[NewsArticle]:
    if not NEWS_API_KEY:
        return []

    query = {**params, "apiKey": NEWS_API_KEY}
    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(f"{NEWS_API_BASE}/{path}", params=query)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("NewsAPI request failed (%s): %s", path, exc)
        return []

    if payload.get("status") != "ok":
        logger.warning("NewsAPI returned non-ok status: %s", payload.get("message"))
        return []

    articles: list[NewsArticle] = []
    for raw in payload.get("articles") or []:
        if not isinstance(raw, dict):
            continue
        parsed = _article_from_newsapi(raw)
        if parsed is not None:
            articles.append(parsed)
    return articles


def _fallback_articles(language: str) -> list[NewsArticle]:
    raw_list = _FALLBACK_ARTICLES_ZH if language == "zh" else _FALLBACK_ARTICLES
    articles: list[NewsArticle] = []
    for raw in raw_list:
        parsed = _article_from_newsapi(raw)
        if parsed is not None:
            articles.append(parsed)
    return articles


def fetch_recent_news(*, force_refresh: bool = False, language: str = "en") -> list[NewsArticle]:
    """Fetch recent business/tech headlines from NewsAPI with in-memory caching."""
    global _cache

    lang = _normalize_language(language)
    now = datetime.now(timezone.utc)
    cached = _cache.get(lang)
    if (
        not force_refresh
        and cached is not None
        and (now - cached.fetched_at).total_seconds() < CACHE_TTL_SECONDS
    ):
        return list(cached.articles)

    articles: list[NewsArticle] = []
    if lang == "zh":
        articles.extend(
            _fetch_newsapi(
                "top-headlines",
                {
                    "country": "cn",
                    "category": "business",
                    "language": "zh",
                    "pageSize": 100,
                },
            )
        )
        articles.extend(
            _fetch_newsapi(
                "top-headlines",
                {
                    "country": "cn",
                    "category": "technology",
                    "language": "zh",
                    "pageSize": 100,
                },
            )
        )
        articles.extend(
            _fetch_newsapi(
                "everything",
                {
                    "q": "比特币 OR 英伟达 OR 半导体 OR ETF OR 芯片",
                    "language": "zh",
                    "sortBy": "publishedAt",
                    "pageSize": 50,
                },
            )
        )
    else:
        articles.extend(
            _fetch_newsapi(
                "top-headlines",
                {
                    "category": "business",
                    "language": "en",
                    "pageSize": 100,
                },
            )
        )
        articles.extend(
            _fetch_newsapi(
                "top-headlines",
                {
                    "category": "technology",
                    "language": "en",
                    "pageSize": 100,
                },
            )
        )
        articles.extend(
            _fetch_newsapi(
                "everything",
                {
                    "q": "bitcoin OR nvidia OR semiconductor OR ETF",
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 50,
                },
            )
        )

    articles = _dedupe_articles(articles)
    if not articles:
        logger.info(
            "Using fallback news articles for language=%s (NewsAPI unavailable or empty)",
            lang,
        )
        articles = _fallback_articles(lang)

    articles.sort(key=lambda item: item.published_at, reverse=True)
    _cache[lang] = _NewsCache(fetched_at=now, articles=articles)
    return list(articles)


def _contains_cjk(text: str) -> bool:
    return re.search(r"[\u4e00-\u9fff]", text) is not None


def _is_strong_keyword(keyword: str) -> bool:
    if _contains_cjk(keyword):
        return len(keyword) >= 2
    return len(keyword) >= 5


def _keyword_hit(text: str, keyword: str) -> bool:
    if not keyword:
        return False
    if _contains_cjk(keyword):
        return keyword in text
    kw_lower = keyword.lower()
    text_lower = text.lower()
    if " " in keyword:
        return kw_lower in text_lower
    return re.search(rf"\b{re.escape(kw_lower)}\b", text_lower) is not None


def compute_match_score(article: NewsArticle, symbol: str, *, language: str = "en") -> int:
    """Score how relevant a news article is to a portfolio symbol (0–100)."""
    lang = _normalize_language(language)
    profile = _profile_for(symbol)
    title = article.title
    body = f"{article.title} {article.summary}"

    best = 0
    for keyword in _keywords_for(profile, lang):
        kw = keyword.lower() if not _contains_cjk(keyword) else keyword
        score = 0
        if _keyword_hit(title, keyword):
            score = 87 if _is_strong_keyword(keyword) else 80
        elif _keyword_hit(body, keyword):
            score = 65 if _is_strong_keyword(keyword) else 58
        best = max(best, score)

    if best == 0:
        return 0

    secondary_boost = 0
    for secondary in _secondary_for(profile, lang):
        if _keyword_hit(title, secondary):
            secondary_boost = max(
                secondary_boost,
                11 if secondary.lower() == "etf" else 8,
            )
        elif _keyword_hit(body, secondary):
            secondary_boost = max(secondary_boost, 4)

    best = min(100, best + secondary_boost)

    ticker = _normalize_symbol(symbol).split("-")[0].lower()
    if len(ticker) >= 2 and _keyword_hit(title, ticker):
        best = min(100, best + 5)

    return best


def _priority_for(score: int) -> str:
    if score >= 90:
        return "high"
    if score >= 70:
        return "medium"
    return "low"


def _why_this_matters(
    related: list[str],
    profile_labels: list[str],
    *,
    language: str,
) -> str:
    if not related:
        if language == "zh":
            return "该头条可能影响您组合的整体市场情绪。"
        return "This headline may affect broader market sentiment for your portfolio."
    labels = "、".join(profile_labels) if profile_labels else "、".join(related)
    if language == "zh":
        return f"您持有 {labels}，该新闻可能与您的持仓存在直接或间接关联。"
    return f"You hold {labels}. This news may be directly or indirectly relevant to your holdings."


def _relevance_reason(score: int, matched_label: str, *, language: str) -> str:
    if language == "zh":
        if score >= 90:
            return f"新闻标题与 {matched_label} 高度相关。"
        if score >= 70:
            return f"新闻内容与 {matched_label} 存在明确关联。"
        return f"新闻主题与 {matched_label} 存在间接关联。"
    if score >= 90:
        return f"Headline is highly relevant to {matched_label}."
    if score >= 70:
        return f"Article content is clearly linked to {matched_label}."
    return f"Topic is indirectly related to {matched_label}."


def _infer_category(symbols: list[str]) -> str:
    categories = {_profile_for(s)["category"] for s in symbols}
    if len(categories) == 1:
        return next(iter(categories))
    return "macro"


def _holding_display_names(symbols: list[str], *, language: str) -> list[str]:
    return [lookup_symbol(s, language=language).name for s in symbols]


def article_to_feed_item(
    article: NewsArticle,
    *,
    related_holdings: list[str],
    relevance_score: int,
    language: str = "en",
) -> FeedItem:
    lang = _normalize_language(language)
    labels = _holding_display_names(related_holdings, language=lang)
    primary_label = labels[0] if labels else "portfolio"
    priority = _priority_for(relevance_score)
    confidence = max(60, min(98, relevance_score - 2))

    return FeedItem(
        id=article.id,
        title=article.title,
        summary=article.summary,
        ai_summary=article.summary,
        why_this_matters=_why_this_matters(related_holdings, labels, language=lang),
        related_holdings=related_holdings,
        priority=priority,
        impact=priority,
        relevance_score=relevance_score,
        ai_confidence=confidence,
        published_at=article.published_at,
        source=article.source,
        url=article.url,
        event_category=_infer_category(related_holdings) if related_holdings else "macro",
        relevance_reason=_relevance_reason(relevance_score, primary_label, language=lang),
    )


def articles_to_feed_items(articles: list[NewsArticle], *, language: str = "en") -> list[FeedItem]:
    """Convert raw news articles to feed items without portfolio matching."""
    lang = _normalize_language(language)
    why = (
        "最新市场要闻。"
        if lang == "zh"
        else "Latest market headline from your news feed."
    )
    reason = "综合市场新闻。" if lang == "zh" else "General market news."
    return [
        FeedItem(
            id=article.id,
            title=article.title,
            summary=article.summary,
            ai_summary=article.summary,
            why_this_matters=why,
            related_holdings=[],
            priority="medium",
            impact="medium",
            relevance_score=0,
            ai_confidence=70,
            published_at=article.published_at,
            source=article.source,
            url=article.url,
            event_category="macro",
            relevance_reason=reason,
        )
        for article in articles
    ]


def match_news_to_portfolio(
    articles: list[NewsArticle],
    symbols: list[str],
    *,
    min_score: int = 55,
    language: str = "en",
) -> list[FeedItem]:
    """Match cached/fetched news against portfolio symbols and return ranked feed items."""
    if not symbols:
        return []

    normalized_symbols = [_normalize_symbol(s) for s in symbols if s.strip()]
    if not normalized_symbols:
        return []

    article_matches: dict[str, tuple[NewsArticle, list[str], int]] = {}

    for article in articles:
        matched_symbols: list[str] = []
        best_score = 0

        for symbol in normalized_symbols:
            score = compute_match_score(article, symbol, language=language)
            if score >= min_score:
                matched_symbols.append(symbol)
                best_score = max(best_score, score)

        if not matched_symbols:
            continue

        existing = article_matches.get(article.id)
        if existing is None or best_score > existing[2]:
            article_matches[article.id] = (article, matched_symbols, best_score)

    items = [
        article_to_feed_item(
            article,
            related_holdings=matched,
            relevance_score=score,
            language=language,
        )
        for article, matched, score in article_matches.values()
    ]
    items.sort(key=lambda item: (item.relevance_score, item.published_at), reverse=True)
    return items


def get_recent_news(*, force_refresh: bool = False, language: str = "en") -> list[FeedItem]:
    lang = _normalize_language(language)
    articles = fetch_recent_news(force_refresh=force_refresh, language=lang)
    return articles_to_feed_items(articles, language=lang)


def get_personalized_feed(symbols: list[str], *, language: str = "en") -> list[FeedItem]:
    lang = _normalize_language(language)
    articles = fetch_recent_news(language=lang)
    return match_news_to_portfolio(articles, symbols, language=lang)

"""Keyword-based relevance scoring — swappable with semantic/LLM scoring."""

from __future__ import annotations

from app.services.news_service import (
    NewsArticle,
    compute_match_score,
    match_news_to_portfolio,
)
from app.schemas.feed import FeedItem

__all__ = [
    "NewsArticle",
    "compute_match_score",
    "match_news_to_portfolio",
    "rank_feed_items",
]


def rank_feed_items(items: list[FeedItem]) -> list[FeedItem]:
    return sorted(items, key=lambda item: (item.relevance_score, item.published_at), reverse=True)

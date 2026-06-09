"""Feed orchestration with database persistence."""

from __future__ import annotations

from app.repositories.feed_repository import FeedRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.schemas.feed import FeedItem
from app.services.intelligence_service import enrich_feed_items
from app.services.news_service import get_personalized_feed


class FeedService:
    def __init__(
        self,
        *,
        portfolio_repo: PortfolioRepository,
        feed_repo: FeedRepository,
        user_id: int,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._feed_repo = feed_repo
        self._user_id = user_id

    async def get_feed(self, symbols: list[str] | None = None, *, language: str = "en") -> list[FeedItem]:
        symbol_list = [s.strip() for s in (symbols or []) if s.strip()]
        if not symbol_list:
            symbol_list = await self._portfolio_repo.get_symbols(self._user_id)

        items = get_personalized_feed(symbol_list, language=language)
        enriched = enrich_feed_items(items, language=language)
        await self._feed_repo.upsert_items(enriched)
        return enriched

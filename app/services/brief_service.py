"""Morning brief orchestration with database persistence."""

from __future__ import annotations

import hashlib
from datetime import date

from app.ai.brief_generator import generate_brief
from app.repositories.brief_repository import BriefRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.schemas.brief import MorningBriefResponse
from app.services.cache_service import brief_cache
from app.services.feed_service import FeedService


def _cache_key(symbols: list[str], language: str) -> str:
    today = date.today().isoformat()
    sym_key = ",".join(sorted(s.strip().upper() for s in symbols if s.strip()))
    digest = hashlib.sha256(f"{today}|{sym_key}|{language}".encode()).hexdigest()
    return digest[:20]


class BriefService:
    def __init__(
        self,
        *,
        portfolio_repo: PortfolioRepository,
        feed_service: FeedService,
        brief_repo: BriefRepository,
        user_id: int,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._feed_service = feed_service
        self._brief_repo = brief_repo
        self._user_id = user_id

    async def get_morning_brief(
        self,
        symbols: list[str] | None = None,
        *,
        language: str = "en",
        force_refresh: bool = False,
    ) -> MorningBriefResponse:
        symbol_list = [s.strip() for s in (symbols or []) if s.strip()]
        if not symbol_list:
            symbol_list = await self._portfolio_repo.get_symbols(self._user_id)

        lang = "zh" if language.lower().startswith("zh") else "en"
        key = _cache_key(symbol_list, lang)

        if not force_refresh:
            cached = brief_cache.get(key)
            if cached is not None:
                return MorningBriefResponse.model_validate(cached)

        items = await self._feed_service.get_feed(symbol_list, language=lang)
        brief = generate_brief(items, symbol_list, language=lang)
        brief_cache.set(key, brief.model_dump(mode="json"))

        await self._brief_repo.save(
            self._user_id,
            headline=brief.headline,
            summary=brief.summary,
        )
        return brief

    async def get_history(self, *, limit: int = 10) -> list[dict]:
        records = await self._brief_repo.get_latest(self._user_id, limit=limit)
        return [
            {
                "id": record.id,
                "headline": record.headline,
                "summary": record.summary,
                "created_at": record.created_at.isoformat(),
            }
            for record in records
        ]

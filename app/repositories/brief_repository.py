"""Morning brief history persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brief_history import BriefHistory


class BriefRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, user_id: int, headline: str, summary: str) -> BriefHistory:
        record = BriefHistory(
            user_id=user_id,
            headline=headline,
            summary=summary,
        )
        self._session.add(record)
        await self._session.flush()
        await self._session.refresh(record)
        return record

    async def get_latest(self, user_id: int, *, limit: int = 10) -> list[BriefHistory]:
        rows = await self._session.scalars(
            select(BriefHistory)
            .where(BriefHistory.user_id == user_id)
            .order_by(BriefHistory.created_at.desc())
            .limit(limit)
        )
        return list(rows.all())

    async def get_latest_one(self, user_id: int) -> BriefHistory | None:
        rows = await self.get_latest(user_id, limit=1)
        return rows[0] if rows else None

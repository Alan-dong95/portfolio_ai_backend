"""Persist and query feed items."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feed_item import FeedItem as FeedItemModel
from app.schemas.feed import FeedItem


class FeedRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_items(self, items: list[FeedItem]) -> None:
        if not items:
            return

        for item in items:
            existing = await self._session.get(FeedItemModel, item.id)
            if existing is None:
                self._session.add(
                    FeedItemModel(
                        id=item.id,
                        title=item.title,
                        summary=item.summary,
                        source=item.source,
                        url=item.url,
                        published_at=item.published_at,
                    )
                )
            else:
                existing.title = item.title
                existing.summary = item.summary
                existing.source = item.source
                existing.url = item.url
                existing.published_at = item.published_at
        await self._session.flush()

    async def get_by_id(self, feed_item_id: str) -> FeedItemModel | None:
        return await self._session.get(FeedItemModel, feed_item_id)

    async def get_by_ids(self, feed_item_ids: list[str]) -> list[FeedItemModel]:
        if not feed_item_ids:
            return []
        rows = await self._session.scalars(
            select(FeedItemModel).where(FeedItemModel.id.in_(feed_item_ids))
        )
        return list(rows.all())

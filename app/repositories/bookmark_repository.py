"""User bookmark persistence."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bookmark import Bookmark


class BookmarkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_feed_item_ids(self, user_id: int) -> list[str]:
        rows = await self._session.scalars(
            select(Bookmark.feed_item_id)
            .where(Bookmark.user_id == user_id)
            .order_by(Bookmark.created_at.desc())
        )
        return list(rows.all())

    async def add(self, user_id: int, feed_item_id: str) -> bool:
        existing = await self._session.scalar(
            select(Bookmark.id).where(
                Bookmark.user_id == user_id,
                Bookmark.feed_item_id == feed_item_id,
            )
        )
        if existing is not None:
            return False

        self._session.add(
            Bookmark(
                user_id=user_id,
                feed_item_id=feed_item_id,
            )
        )
        await self._session.flush()
        return True

    async def remove(self, user_id: int, feed_item_id: str) -> bool:
        result = await self._session.execute(
            delete(Bookmark).where(
                Bookmark.user_id == user_id,
                Bookmark.feed_item_id == feed_item_id,
            )
        )
        await self._session.flush()
        return result.rowcount > 0

    async def is_bookmarked(self, user_id: int, feed_item_id: str) -> bool:
        row = await self._session.scalar(
            select(Bookmark.id).where(
                Bookmark.user_id == user_id,
                Bookmark.feed_item_id == feed_item_id,
            )
        )
        return row is not None

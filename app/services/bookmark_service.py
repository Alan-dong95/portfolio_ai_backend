"""Bookmark orchestration service."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.repositories.bookmark_repository import BookmarkRepository
from app.repositories.feed_repository import FeedRepository


class BookmarkService:
    def __init__(
        self,
        *,
        bookmark_repo: BookmarkRepository,
        feed_repo: FeedRepository,
        user_id: int,
    ) -> None:
        self._bookmark_repo = bookmark_repo
        self._feed_repo = feed_repo
        self._user_id = user_id

    async def list_bookmarks(self) -> list[str]:
        return await self._bookmark_repo.list_feed_item_ids(self._user_id)

    async def add_bookmark(self, feed_item_id: str) -> list[str]:
        feed_item = await self._feed_repo.get_by_id(feed_item_id)
        if feed_item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feed item not found: {feed_item_id}",
            )
        await self._bookmark_repo.add(self._user_id, feed_item_id)
        return await self.list_bookmarks()

    async def remove_bookmark(self, feed_item_id: str) -> list[str]:
        removed = await self._bookmark_repo.remove(self._user_id, feed_item_id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bookmark not found: {feed_item_id}",
            )
        return await self.list_bookmarks()

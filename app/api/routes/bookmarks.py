from fastapi import APIRouter, Depends

from app.api.dependencies import get_bookmark_service
from app.services.bookmark_service import BookmarkService

router = APIRouter()


@router.get("/")
async def list_bookmarks(service: BookmarkService = Depends(get_bookmark_service)):
    ids = await service.list_bookmarks()
    return {"bookmarks": ids}


@router.post("/{feed_item_id}")
async def add_bookmark(
    feed_item_id: str,
    service: BookmarkService = Depends(get_bookmark_service),
):
    ids = await service.add_bookmark(feed_item_id)
    return {"bookmarks": ids}


@router.delete("/{feed_item_id}")
async def remove_bookmark(
    feed_item_id: str,
    service: BookmarkService = Depends(get_bookmark_service),
):
    ids = await service.remove_bookmark(feed_item_id)
    return {"bookmarks": ids}

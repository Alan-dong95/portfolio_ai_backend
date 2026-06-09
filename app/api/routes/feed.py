from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_feed_service
from app.schemas.feed import FeedItem
from app.services.feed_service import FeedService

router = APIRouter()


@router.get("/", response_model=list[FeedItem])
async def fetch_feed(
    symbols: str | None = Query(default=None),
    language: str = Query(default="en", description="News language: en or zh"),
    service: FeedService = Depends(get_feed_service),
):
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()] if symbols else []
    return await service.get_feed(symbol_list, language=language)

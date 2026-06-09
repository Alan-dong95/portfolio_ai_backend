from fastapi import APIRouter, Query

from app.schemas.feed import FeedItem
from app.services.news_service import get_recent_news

router = APIRouter()


@router.get("/", response_model=list[FeedItem])
def fetch_news(
    refresh: bool = Query(default=False, description="Bypass cache and refetch"),
    language: str = Query(default="en", description="News language: en or zh"),
):
    return get_recent_news(force_refresh=refresh, language=language)

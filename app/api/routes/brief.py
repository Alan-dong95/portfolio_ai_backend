from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_brief_service
from app.schemas.brief import MorningBriefResponse
from app.services.brief_service import BriefService

router = APIRouter()


@router.get("/", response_model=MorningBriefResponse)
async def fetch_brief(
    symbols: str | None = Query(default=None),
    language: str = Query(default="en", description="Brief language: en or zh"),
    refresh: bool = Query(default=False, description="Bypass brief cache"),
    service: BriefService = Depends(get_brief_service),
):
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()] if symbols else []
    return await service.get_morning_brief(symbol_list, language=language, force_refresh=refresh)


@router.get("/history")
async def fetch_brief_history(
    limit: int = Query(default=10, ge=1, le=50),
    service: BriefService = Depends(get_brief_service),
):
    return await service.get_history(limit=limit)

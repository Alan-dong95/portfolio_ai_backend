from fastapi import APIRouter, Depends

from app.api.dependencies import get_portfolio_service
from app.services.portfolio_service import PortfolioService

router = APIRouter()


@router.get("/")
async def fetch_portfolio(service: PortfolioService = Depends(get_portfolio_service)):
    return await service.get_symbols()

from fastapi import APIRouter, Query

from app.schemas.symbol import SymbolInfo
from app.services.symbol_service import lookup_symbols

router = APIRouter()


@router.get("/lookup", response_model=list[SymbolInfo])
def fetch_symbol_names(
    symbols: str = Query(..., description="Comma-separated symbols, e.g. NVDA,301392,BTC-USD"),
    language: str = Query(default="en", description="Display language: en or zh"),
):
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    return lookup_symbols(symbol_list, language=language)

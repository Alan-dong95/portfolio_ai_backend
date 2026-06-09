from pydantic import BaseModel


class SymbolInfo(BaseModel):
    symbol: str
    name: str
    kind: str = "stock"

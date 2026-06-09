from pydantic import BaseModel, Field


class PortfolioSymbolsResponse(BaseModel):
    symbols: list[str] = Field(
        ...,
        description="User portfolio ticker symbols",
        examples=[["301392", "BTC-USD"]],
    )

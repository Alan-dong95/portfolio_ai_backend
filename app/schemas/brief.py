from typing import List

from pydantic import BaseModel, Field


class MorningBriefResponse(BaseModel):
    headline: str
    summary: str
    top_risks: List[str] = Field(default_factory=list)
    top_opportunities: List[str] = Field(default_factory=list)
    high_impact_count: int = 0
    exposure_sectors: List[str] = Field(default_factory=list)

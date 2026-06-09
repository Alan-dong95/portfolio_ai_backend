from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class FeedItem(BaseModel):
    id: str
    title: str
    summary: str
    ai_summary: str = ""
    why_this_matters: str
    related_holdings: List[str]
    priority: str
    impact: str = "medium"
    relevance_score: int
    ai_confidence: int
    published_at: datetime
    source: str = ""
    url: str = ""
    event_category: str = "macro"
    relevance_reason: str = ""


class FeedListResponse(BaseModel):
    items: List[FeedItem] = Field(default_factory=list)

"""Re-export LLM service from ai package for modular imports."""

from app.ai.llm_service import NewsIntel, analyze_news

__all__ = ["NewsIntel", "analyze_news"]

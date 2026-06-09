"""FastAPI dependency injection for repositories and services."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.init_db import DEFAULT_USER_EMAIL
from app.db.session import get_db
from app.models.user import User
from app.repositories.bookmark_repository import BookmarkRepository
from app.repositories.brief_repository import BriefRepository
from app.repositories.feed_repository import FeedRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.services.bookmark_service import BookmarkService
from app.services.brief_service import BriefService
from app.services.feed_service import FeedService
from app.services.portfolio_service import PortfolioService


async def get_default_user_id(session: AsyncSession) -> int:
    user_id = await session.scalar(select(User.id).where(User.email == DEFAULT_USER_EMAIL))
    if user_id is None:
        raise RuntimeError(f"Default user not found: {DEFAULT_USER_EMAIL}")
    return user_id


async def get_portfolio_service(
    session: AsyncSession = Depends(get_db),
) -> PortfolioService:
    user_id = await get_default_user_id(session)
    return PortfolioService(PortfolioRepository(session), user_id=user_id)


async def get_feed_service(
    session: AsyncSession = Depends(get_db),
) -> FeedService:
    user_id = await get_default_user_id(session)
    return FeedService(
        portfolio_repo=PortfolioRepository(session),
        feed_repo=FeedRepository(session),
        user_id=user_id,
    )


async def get_brief_service(
    session: AsyncSession = Depends(get_db),
) -> BriefService:
    user_id = await get_default_user_id(session)
    return BriefService(
        portfolio_repo=PortfolioRepository(session),
        feed_service=FeedService(
            portfolio_repo=PortfolioRepository(session),
            feed_repo=FeedRepository(session),
            user_id=user_id,
        ),
        brief_repo=BriefRepository(session),
        user_id=user_id,
    )


async def get_bookmark_service(
    session: AsyncSession = Depends(get_db),
) -> BookmarkService:
    user_id = await get_default_user_id(session)
    return BookmarkService(
        bookmark_repo=BookmarkRepository(session),
        feed_repo=FeedRepository(session),
        user_id=user_id,
    )

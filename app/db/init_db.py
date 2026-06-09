"""Seed default user and portfolio on startup."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Portfolio
from app.models.user import User

logger = logging.getLogger(__name__)

DEFAULT_USER_EMAIL = "default@portfolio.ai"
DEFAULT_SYMBOLS: list[tuple[str, str]] = [
    ("301392", "stock"),
    ("BTC-USD", "crypto"),
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def ensure_default_user(session: AsyncSession) -> User:
    user = await session.scalar(select(User).where(User.email == DEFAULT_USER_EMAIL))
    if user is not None:
        return user

    user = User(email=DEFAULT_USER_EMAIL, created_at=_utcnow())
    session.add(user)
    await session.flush()
    logger.info("Created default user id=%s email=%s", user.id, user.email)
    return user


async def ensure_default_portfolio(session: AsyncSession, user_id: int) -> None:
    existing = await session.scalar(
        select(Portfolio.id).where(Portfolio.user_id == user_id).limit(1)
    )
    if existing is not None:
        return

    now = _utcnow()
    for symbol, asset_type in DEFAULT_SYMBOLS:
        session.add(
            Portfolio(
                user_id=user_id,
                symbol=symbol,
                asset_type=asset_type,
                created_at=now,
            )
        )
    await session.flush()
    logger.info("Seeded default portfolio for user_id=%s", user_id)


async def init_db(session: AsyncSession) -> None:
    user = await ensure_default_user(session)
    await ensure_default_portfolio(session, user.id)

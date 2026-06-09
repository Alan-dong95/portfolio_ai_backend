"""PostgreSQL portfolio repository (async SQLAlchemy 2.0)."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Portfolio


class PortfolioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_symbols(self, user_id: int) -> list[str]:
        rows = await self._session.scalars(
            select(Portfolio.symbol)
            .where(Portfolio.user_id == user_id)
            .order_by(Portfolio.created_at)
        )
        return list(rows.all())

    async def set_symbols(
        self,
        user_id: int,
        symbols: list[str],
        *,
        asset_type: str = "stock",
    ) -> None:
        cleaned = [s.strip() for s in symbols if s.strip()]
        await self._session.execute(delete(Portfolio).where(Portfolio.user_id == user_id))
        for symbol in cleaned:
            self._session.add(
                Portfolio(
                    user_id=user_id,
                    symbol=symbol,
                    asset_type=asset_type,
                )
            )
        await self._session.flush()

    async def replace_symbols_with_types(
        self,
        user_id: int,
        holdings: list[tuple[str, str]],
    ) -> None:
        await self._session.execute(delete(Portfolio).where(Portfolio.user_id == user_id))
        for symbol, asset_type in holdings:
            self._session.add(
                Portfolio(
                    user_id=user_id,
                    symbol=symbol,
                    asset_type=asset_type,
                )
            )
        await self._session.flush()

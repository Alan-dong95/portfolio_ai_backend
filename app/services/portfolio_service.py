from app.repositories.portfolio_repository import PortfolioRepository


class PortfolioService:
    def __init__(self, portfolio_repo: PortfolioRepository, *, user_id: int) -> None:
        self._portfolio_repo = portfolio_repo
        self._user_id = user_id

    async def get_symbols(self) -> list[str]:
        return await self._portfolio_repo.get_symbols(self._user_id)

    async def set_symbols(self, symbols: list[str]) -> list[str]:
        await self._portfolio_repo.set_symbols(self._user_id, symbols)
        return await self.get_symbols()

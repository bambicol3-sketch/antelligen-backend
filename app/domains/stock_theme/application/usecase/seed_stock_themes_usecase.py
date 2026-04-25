from app.domains.stock_theme.application.port.out.stock_theme_repository_port import StockThemeRepositoryPort
from app.domains.stock_theme.domain.entity.stock_theme import StockTheme
from app.domains.stock_theme.domain.service.stock_theme_seed_data import ALL_THEME_STOCK_SEED


class SeedStockThemesUseCase:
    def __init__(self, repository: StockThemeRepositoryPort):
        self._repository = repository

    async def execute(self) -> None:
        seed_entities = [
            StockTheme(id=None, name=item["name"], code=item["code"], themes=item["themes"])
            for item in ALL_THEME_STOCK_SEED
        ]
        await self._repository.save_all(seed_entities)

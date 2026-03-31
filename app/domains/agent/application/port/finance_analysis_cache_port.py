from abc import ABC, abstractmethod
from typing import Any


class FinanceAnalysisCachePort(ABC):
    @abstractmethod
    async def get(self, cache_key: str) -> dict[str, Any] | None:
        pass

    @abstractmethod
    async def set(self, cache_key: str, payload: dict[str, Any]) -> None:
        pass

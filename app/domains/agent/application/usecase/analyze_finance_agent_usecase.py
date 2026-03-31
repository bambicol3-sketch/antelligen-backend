import hashlib
import uuid

from app.common.exception.app_exception import AppException
from app.domains.agent.application.port.finance_analysis_cache_port import (
    FinanceAnalysisCachePort,
)
from app.domains.agent.application.port.finance_agent_provider import (
    FinanceAgentProvider,
)
from app.domains.agent.application.request.finance_analysis_request import (
    FinanceAnalysisRequest,
)
from app.domains.agent.application.response.agent_query_response import (
    AgentQueryResponse,
)
from app.domains.agent.application.response.sub_agent_response import SubAgentResponse
from app.domains.stock.application.port.stock_repository import StockRepository
from app.domains.stock.application.response.stock_collection_response import (
    StockCollectionResponse,
)
from app.domains.stock.application.usecase.get_stored_stock_data_usecase import (
    GetStoredStockDataUseCase,
)
from app.domains.stock.domain.entity.stock import Stock


class AnalyzeFinanceAgentUseCase:
    """Run finance analysis using stored stock data."""

    def __init__(
        self,
        stock_repository: StockRepository,
        get_stored_stock_data_usecase: GetStoredStockDataUseCase,
        finance_agent_provider: FinanceAgentProvider,
        finance_analysis_cache: FinanceAnalysisCachePort | None = None,
    ):
        self._stock_repository = stock_repository
        self._get_stored_stock_data_usecase = get_stored_stock_data_usecase
        self._finance_agent_provider = finance_agent_provider
        self._finance_analysis_cache = finance_analysis_cache

    async def execute(self, request: FinanceAnalysisRequest) -> AgentQueryResponse:
        stock = await self._resolve_stock(request)
        stock_data = await self._get_stored_stock_data_usecase.execute(stock.ticker)

        finance_result: SubAgentResponse | None = None
        answer: str | None = None
        cache_key = self._build_cache_key(
            ticker=stock.ticker,
            user_query=request.query,
            stock_data=stock_data,
        )

        if self._finance_analysis_cache is not None:
            cached_payload = await self._finance_analysis_cache.get(cache_key)
            if cached_payload:
                finance_result = SubAgentResponse.model_validate(
                    cached_payload["finance_result"]
                )
                answer = cached_payload["answer"]
                finance_result.data = {
                    **(finance_result.data or {}),
                    "cache_hit": True,
                }

        if finance_result is None:
            finance_result = await self._finance_agent_provider.analyze(
                user_query=request.query,
                stock_data=stock_data,
            )
            finance_result.data = {
                **(finance_result.data or {}),
                "cache_hit": False,
            }
            answer = self._build_answer(finance_result)

            if self._finance_analysis_cache is not None:
                await self._finance_analysis_cache.set(
                    cache_key,
                    {
                        "answer": answer,
                        "finance_result": finance_result.model_dump(mode="json"),
                    },
                )

        return AgentQueryResponse(
            session_id=request.session_id or str(uuid.uuid4()),
            result_status=AgentQueryResponse.determine_status([finance_result]),
            answer=answer or self._build_answer(finance_result),
            agent_results=[finance_result],
            total_execution_time_ms=finance_result.execution_time_ms,
        )

    async def _resolve_stock(self, request: FinanceAnalysisRequest) -> Stock:
        if request.ticker:
            stock = await self._stock_repository.find_by_ticker(request.ticker)
            if stock:
                return stock

        if request.company_name:
            stock = await self._stock_repository.find_by_company_name(request.company_name)
            if stock:
                return stock

        raise AppException(
            status_code=404,
            message="분석할 종목을 찾을 수 없습니다.",
        )

    def _build_answer(self, finance_result: SubAgentResponse) -> str:
        signal = finance_result.get_investment_signal()
        if signal is None:
            return "재무분석 결과를 생성하지 못했습니다."

        points = " ".join(
            f"{index + 1}. {point}" for index, point in enumerate(signal.key_points)
        )
        return f"{signal.summary} {points}".strip()

    def _build_cache_key(
        self,
        *,
        ticker: str,
        user_query: str,
        stock_data: StockCollectionResponse,
    ) -> str:
        normalized_query = " ".join(user_query.split()).strip().lower()
        raw_key = "::".join(
            [
                ticker,
                stock_data.metadata.dedup_key,
                normalized_query,
            ]
        )
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

import time

from app.domains.agent.application.port.finance_agent_port import FinanceAgentPort
from app.domains.agent.application.request.finance_analysis_request import FinanceAnalysisRequest
from app.domains.agent.application.response.sub_agent_response import SubAgentResponse
from app.domains.agent.application.usecase.analyze_finance_agent_usecase import (
    AnalyzeFinanceAgentUseCase,
)
from app.domains.agent.adapter.outbound.external.langgraph_finance_agent_provider import (
    LangGraphFinanceAgentProvider,
)
from app.domains.stock.adapter.outbound.persistence.stock_repository_impl import (
    StockRepositoryImpl,
)
from app.domains.stock.adapter.outbound.persistence.stock_vector_repository_impl import (
    StockVectorRepositoryImpl,
)
from app.domains.stock.application.usecase.get_stored_stock_data_usecase import (
    GetStoredStockDataUseCase,
)
from app.infrastructure.config.settings import get_settings


class FinanceSubAgentAdapter(FinanceAgentPort):
    """재무 분석 UseCase를 호출하는 아웃바운드 어댑터."""

    async def analyze(self, ticker: str, query: str) -> SubAgentResponse:
        start = time.monotonic()
        try:
            settings = get_settings()
            stock_repository = StockRepositoryImpl()
            stock_vector_repository = StockVectorRepositoryImpl()

            get_stored_stock_data_usecase = GetStoredStockDataUseCase(
                stock_repository=stock_repository,
                stock_vector_repository=stock_vector_repository,
            )
            finance_provider = LangGraphFinanceAgentProvider(
                api_key=settings.openai_api_key,
                chat_model=settings.openai_finance_agent_model,
                embedding_model=settings.openai_embedding_model,
                top_k=settings.finance_rag_top_k,
                langsmith_tracing=settings.langsmith_tracing,
                langsmith_api_key=settings.langsmith_api_key,
                langsmith_project=settings.langsmith_project,
                langsmith_endpoint=settings.langsmith_endpoint,
            )
            usecase = AnalyzeFinanceAgentUseCase(
                stock_repository=stock_repository,
                get_stored_stock_data_usecase=get_stored_stock_data_usecase,
                finance_agent_provider=finance_provider,
            )

            request = FinanceAnalysisRequest(ticker=ticker, query=query)
            result = await usecase.execute(request)

            elapsed = int((time.monotonic() - start) * 1000)
            if result.agent_results:
                return result.agent_results[0]
            return SubAgentResponse.no_data("finance", elapsed)

        except Exception as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            return SubAgentResponse.error("finance", str(exc), elapsed)

from app.common.exception.app_exception import AppException
from app.domains.account.application.port.out.account_repository_port import AccountRepositoryPort
from app.domains.account.application.port.out.account_save_port import AccountSavePort
from app.domains.account.application.port.out.stock_master_port import StockMasterPort
from app.domains.account.application.port.out.watchlist_save_port import WatchlistSavePort
from app.domains.account.application.request.signup_request import SignupRequest
from app.domains.account.application.response.signup_response import SignupResponse, WatchlistStockItem
from app.domains.account.domain.entity.account import Account


class SignupUseCase:
    def __init__(
        self,
        account_repository: AccountRepositoryPort,
        account_save_port: AccountSavePort,
        stock_master_port: StockMasterPort,
        watchlist_save_port: WatchlistSavePort,
    ):
        self._account_repository = account_repository
        self._account_save_port = account_save_port
        self._stock_master_port = stock_master_port
        self._watchlist_save_port = watchlist_save_port

    async def execute(self, request: SignupRequest) -> SignupResponse:
        existing = await self._account_repository.find_by_email(request.email)
        if existing is not None:
            raise AppException(status_code=409, message="이미 사용 중인 이메일입니다.")

        requested_codes = list(dict.fromkeys(request.watchlist or []))  # 중복 제거, 순서 유지

        if requested_codes:
            found_items = await self._stock_master_port.find_by_codes(requested_codes)
            found_codes = {item.stock_code for item in found_items}
            invalid_codes = [c for c in requested_codes if c not in found_codes]
            if invalid_codes:
                raise AppException(
                    status_code=400,
                    message=f"존재하지 않는 종목 코드입니다: {', '.join(invalid_codes)}",
                )
        else:
            found_items = []

        account = Account(account_id=None, email=request.email, nickname=request.nickname, kakao_id=None)
        saved_account = await self._account_save_port.save(account)

        if found_items:
            await self._watchlist_save_port.save_all(saved_account.account_id, found_items)

        return SignupResponse(
            account_id=saved_account.account_id,
            email=saved_account.email,
            nickname=saved_account.nickname,
            watchlist=[WatchlistStockItem(code=item.stock_code, name=item.stock_name) for item in found_items],
        )

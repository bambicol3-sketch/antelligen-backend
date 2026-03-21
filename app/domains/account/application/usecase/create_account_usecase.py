import logging

from app.common.exception.app_exception import AppException
from app.domains.account.application.port.out.account_save_port import AccountSavePort
from app.domains.account.application.port.out.account_token_cache_port import AccountTokenCachePort
from app.domains.account.application.port.out.temp_token_port import TempTokenPort
from app.domains.account.application.response.create_account_response import CreateAccountResponse
from app.domains.account.domain.entity.account import Account

logger = logging.getLogger(__name__)


class CreateAccountUseCase:
    def __init__(
        self,
        account_save_port: AccountSavePort,
        temp_token_port: TempTokenPort,
        account_token_cache_port: AccountTokenCachePort,
    ):
        self._account_save_port = account_save_port
        self._temp_token_port = temp_token_port
        self._account_token_cache_port = account_token_cache_port

    async def execute(self, nickname: str, email: str, temp_token_value: str) -> CreateAccountResponse:
        temp_token_data = await self._temp_token_port.find_by_token(temp_token_value)
        if not temp_token_data:
            raise AppException(status_code=401, message="임시 토큰이 유효하지 않거나 만료되었습니다.")

        account = Account(account_id=None, email=email, nickname=nickname, kakao_id=None)
        saved_account = await self._account_save_port.save(account)

        await self._temp_token_port.delete_by_token(temp_token_value)

        await self._account_token_cache_port.save_kakao_token(
            account_id=saved_account.account_id,
            kakao_access_token=temp_token_data.kakao_access_token,
        )

        user_token = await self._account_token_cache_port.issue_user_token(account_id=saved_account.account_id)

        logger.info("[계정 생성 완료] account_id: %s, email: %s", saved_account.account_id, saved_account.email)

        return CreateAccountResponse(
            account_id=saved_account.account_id,
            nickname=saved_account.nickname,
            email=saved_account.email,
            user_token=user_token,
        )

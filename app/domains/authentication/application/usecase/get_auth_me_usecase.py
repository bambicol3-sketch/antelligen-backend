from app.common.exception.app_exception import AppException
from app.domains.authentication.application.port.out.account_info_query_port import AccountInfoQueryPort
from app.domains.authentication.application.port.out.session_query_port import SessionQueryPort
from app.domains.authentication.application.port.out.temp_token_query_port import TempTokenQueryPort
from app.domains.authentication.application.response.auth_me_response import AuthMeResponse, AuthUser


class GetAuthMeUseCase:
    def __init__(
        self,
        temp_token_query_port: TempTokenQueryPort,
        session_query_port: SessionQueryPort,
        account_info_query_port: AccountInfoQueryPort,
    ):
        self._temp_token_query_port = temp_token_query_port
        self._session_query_port = session_query_port
        self._account_info_query_port = account_info_query_port

    async def execute(self, token: str) -> AuthMeResponse:
        # 임시 토큰 확인
        temp_data = await self._temp_token_query_port.find_by_token(token)
        if temp_data:
            print(f"[DEBUG] TEMPORARY token: {token}, nickname: {temp_data.get('nickname')}, email: {temp_data.get('email')}")
            return AuthMeResponse(
                tokenType="TEMPORARY",
                user=AuthUser(
                    id="",
                    email=temp_data.get("email") or "",
                    nickname=temp_data.get("nickname") or "",
                ),
            )

        # 세션 토큰 확인
        account_id = await self._session_query_port.get_account_id_by_session(token)
        if account_id:
            account = await self._account_info_query_port.find_by_id(account_id)
            if account:
                print(f"[DEBUG] PERMANENT token: {token}, nickname: {account.nickname}, email: {account.email}")
                return AuthMeResponse(
                    tokenType="PERMANENT",
                    user=AuthUser(
                        id=str(account.account_id),
                        email=account.email,
                        nickname=account.nickname or "",
                    ),
                )

        raise AppException(status_code=401, message="유효하지 않거나 만료된 토큰입니다.")

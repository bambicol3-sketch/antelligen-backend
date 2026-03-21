from app.common.exception.app_exception import AppException
from app.domains.authentication.application.port.out.temp_token_query_port import TempTokenQueryPort
from app.domains.authentication.application.response.temp_user_info_response import TempUserInfoResponse


class GetTempUserInfoUseCase:
    def __init__(self, temp_token_query_port: TempTokenQueryPort):
        self._temp_token_query_port = temp_token_query_port

    async def execute(self, temp_token: str) -> TempUserInfoResponse:
        data = await self._temp_token_query_port.find_by_token(temp_token)
        if not data:
            raise AppException(status_code=401, message="임시 토큰이 유효하지 않거나 만료되었습니다.")

        return TempUserInfoResponse(
            is_registered=False,
            nickname=data.get("nickname"),
            email=data.get("email"),
        )

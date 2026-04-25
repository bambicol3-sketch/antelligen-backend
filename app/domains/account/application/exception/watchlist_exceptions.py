from app.common.exception.app_exception import AppException


class DuplicateWatchlistStockException(AppException):
    def __init__(self, stock_code: str):
        super().__init__(
            status_code=409,
            message=f"이미 등록된 관심종목입니다: {stock_code}",
        )


class WatchlistStockNotFoundException(AppException):
    def __init__(self, stock_code: str):
        super().__init__(
            status_code=404,
            message=f"관심종목에 등록되지 않은 종목입니다: {stock_code}",
        )

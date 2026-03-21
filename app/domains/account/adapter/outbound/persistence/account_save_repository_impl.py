from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.account.application.port.out.account_save_port import AccountSavePort
from app.domains.account.domain.entity.account import Account
from app.domains.account.infrastructure.mapper.account_mapper import AccountMapper
from app.domains.account.infrastructure.orm.account_orm import AccountOrm


class AccountSaveRepositoryImpl(AccountSavePort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def save(self, account: Account) -> Account:
        orm = AccountOrm(
            email=account.email,
            nickname=account.nickname,
            kakao_id=account.kakao_id,
        )
        self._db.add(orm)
        await self._db.commit()
        await self._db.refresh(orm)
        return AccountMapper.to_entity(orm)

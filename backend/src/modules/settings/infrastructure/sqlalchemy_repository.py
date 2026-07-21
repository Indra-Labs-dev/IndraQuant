from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text, UniqueConstraint, func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Mapped, Session, mapped_column

from src.modules.settings.domain.entities import Setting
from src.shared.infrastructure.database import Base


class SettingModel(Base):
    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("user_id", "setting_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    setting_key: Mapped[str] = mapped_column(String(100), nullable=False)
    setting_value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class SqlAlchemySettingsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_all(self, user_id: int) -> list[Setting]:
        models = self._session.scalars(
            select(SettingModel).where(SettingModel.user_id == user_id)
        )
        return [Setting(key=m.setting_key, value=m.setting_value) for m in models]

    def upsert(self, user_id: int, key: str, value: str) -> Setting:
        statement = mysql_insert(SettingModel).values(
            user_id=user_id, setting_key=key, setting_value=value
        )
        statement = statement.on_duplicate_key_update(
            setting_value=statement.inserted.setting_value
        )
        self._session.execute(statement)
        self._session.flush()
        return Setting(key=key, value=value)

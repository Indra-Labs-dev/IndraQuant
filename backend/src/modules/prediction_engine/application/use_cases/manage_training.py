from pydantic import BaseModel

from src.modules.market_data.domain.repositories import InstrumentRepository
from src.modules.prediction_engine.infrastructure.sqlalchemy_repository import (
    SqlAlchemyTrainingSessionRepository,
)
from src.modules.prediction_engine.infrastructure.training_runner import TrainingRunner


class TrainingSessionInfo(BaseModel):
    instrument_id: int
    symbol: str
    timeframe: str


class TrainingSessionsResponse(BaseModel):
    sessions: list[TrainingSessionInfo]


class ManageTrainingUseCase:
    def __init__(
        self,
        runner: TrainingRunner,
        instruments: InstrumentRepository,
        sessions: SqlAlchemyTrainingSessionRepository,
    ) -> None:
        self._runner = runner
        self._instruments = instruments
        self._sessions = sessions

    async def start(self, timeframe: str, instrument_ids: list[int]) -> TrainingSessionsResponse:
        for instrument_id in instrument_ids:
            self._runner.start(instrument_id, timeframe)
            await self._sessions.set_active(instrument_id, timeframe, True)
        return await self.list_sessions()

    async def stop(self, timeframe: str, instrument_ids: list[int]) -> TrainingSessionsResponse:
        for instrument_id in instrument_ids:
            self._runner.stop(instrument_id, timeframe)
            await self._sessions.set_active(instrument_id, timeframe, False)
        return await self.list_sessions()

    async def list_sessions(self) -> TrainingSessionsResponse:
        all_instruments = await self._instruments.list_instruments()
        symbols = {i.id: i.symbol for i in all_instruments}
        return TrainingSessionsResponse(
            sessions=[
                TrainingSessionInfo(
                    instrument_id=instrument_id,
                    symbol=symbols.get(instrument_id, f"#{instrument_id}"),
                    timeframe=timeframe,
                )
                for instrument_id, timeframe in self._runner.active_sessions()
            ]
        )

from pydantic import BaseModel

from src.modules.market_data.domain.repositories import InstrumentRepository
from src.modules.prediction_engine.infrastructure.training_runner import TrainingRunner


class TrainingSessionInfo(BaseModel):
    instrument_id: int
    symbol: str
    timeframe: str


class TrainingSessionsResponse(BaseModel):
    sessions: list[TrainingSessionInfo]


class ManageTrainingUseCase:
    def __init__(self, runner: TrainingRunner, instruments: InstrumentRepository) -> None:
        self._runner = runner
        self._instruments = instruments

    def start(self, timeframe: str, instrument_ids: list[int]) -> TrainingSessionsResponse:
        for instrument_id in instrument_ids:
            self._runner.start(instrument_id, timeframe)
        return self.list_sessions()

    def stop(self, timeframe: str, instrument_ids: list[int]) -> TrainingSessionsResponse:
        for instrument_id in instrument_ids:
            self._runner.stop(instrument_id, timeframe)
        return self.list_sessions()

    def list_sessions(self) -> TrainingSessionsResponse:
        symbols = {i.id: i.symbol for i in self._instruments.list_instruments()}
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

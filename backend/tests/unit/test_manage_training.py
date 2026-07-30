from src.modules.prediction_engine.application.use_cases.manage_training import (
    ManageTrainingUseCase,
)


class FakeInstrument:
    def __init__(self, id: int, symbol: str) -> None:
        self.id = id
        self.symbol = symbol


class FakeInstrumentRepository:
    def __init__(self, instruments: list[FakeInstrument]) -> None:
        self._instruments = instruments

    async def list_instruments(self, asset_class=None, exchange=None):
        return self._instruments

    async def get(self, instrument_id):
        return next((i for i in self._instruments if i.id == instrument_id), None)


class FakeTrainingRunner:
    def __init__(self) -> None:
        self.started: set[tuple[int, str]] = set()

    def start(self, instrument_id: int, timeframe: str) -> None:
        self.started.add((instrument_id, timeframe))

    def stop(self, instrument_id: int, timeframe: str) -> None:
        self.started.discard((instrument_id, timeframe))

    def active_sessions(self) -> list[tuple[int, str]]:
        return sorted(self.started)


class FakeTrainingSessionRepository:
    """Mirrors `SqlAlchemyTrainingSessionRepository` — persisted "should be
    running" state used to resume sessions after a backend restart."""

    def __init__(self) -> None:
        self._active: dict[tuple[int, str], bool] = {}

    async def set_active(self, instrument_id: int, timeframe: str, is_active: bool) -> None:
        self._active[(instrument_id, timeframe)] = is_active

    async def list_active(self) -> list[tuple[int, str]]:
        return sorted(key for key, active in self._active.items() if active)


INSTRUMENTS = [FakeInstrument(1, "BTC/USDT"), FakeInstrument(2, "ETH/USDT")]


def _make_use_case(runner=None, sessions=None) -> ManageTrainingUseCase:
    return ManageTrainingUseCase(
        runner or FakeTrainingRunner(),
        FakeInstrumentRepository(INSTRUMENTS),
        sessions or FakeTrainingSessionRepository(),
    )


async def test_start_only_affects_requested_instruments():
    use_case = _make_use_case()

    response = await use_case.start("1h", [1])

    assert [s.instrument_id for s in response.sessions] == [1]
    assert response.sessions[0].symbol == "BTC/USDT"


async def test_start_accepts_a_selected_subset_not_all_or_nothing():
    use_case = _make_use_case()

    await use_case.start("1h", [1, 2])
    response = await use_case.list_sessions()

    assert {s.instrument_id for s in response.sessions} == {1, 2}


async def test_stop_only_affects_requested_instruments():
    use_case = _make_use_case()
    await use_case.start("1h", [1, 2])

    response = await use_case.stop("1h", [1])

    assert [s.instrument_id for s in response.sessions] == [2]


async def test_unknown_instrument_id_falls_back_to_placeholder_symbol():
    use_case = _make_use_case()

    response = await use_case.start("1h", [99])

    assert response.sessions[0].symbol == "#99"


async def test_start_persists_active_state_for_resume_after_restart():
    sessions = FakeTrainingSessionRepository()
    use_case = _make_use_case(sessions=sessions)

    await use_case.start("1h", [1, 2])

    assert await sessions.list_active() == [(1, "1h"), (2, "1h")]


async def test_stop_persists_inactive_state_so_it_is_not_resumed():
    sessions = FakeTrainingSessionRepository()
    use_case = _make_use_case(sessions=sessions)
    await use_case.start("1h", [1, 2])

    await use_case.stop("1h", [1])

    assert await sessions.list_active() == [(2, "1h")]

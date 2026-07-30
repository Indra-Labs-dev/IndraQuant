from src.modules.ai_assistant.application.tools import executors as ex
from src.modules.ai_assistant.application.tools.instrument_resolver import (
    resolve_instrument,
)
from src.modules.market_data.application.dto import InstrumentDto, InstrumentsResponse


class FakeListInstruments:
    def __init__(self, instruments: list[InstrumentDto]) -> None:
        self._instruments = instruments

    async def execute(self, *args, **kwargs) -> InstrumentsResponse:
        return InstrumentsResponse(instruments=self._instruments)


_CATALOG = [
    InstrumentDto(id=118, symbol="BTC/USDT", exchange="binance", asset_class="crypto"),
    InstrumentDto(id=119, symbol="ETH/USDT", exchange="binance", asset_class="crypto"),
    InstrumentDto(id=131, symbol="AAPL", exchange="yfinance", asset_class="equity"),
]


async def test_resolve_instrument_exact_match():
    result = await resolve_instrument("BTC/USDT", FakeListInstruments(_CATALOG))
    assert result is not None
    assert result.id == 118


async def test_resolve_instrument_case_insensitive():
    result = await resolve_instrument("btc/usdt", FakeListInstruments(_CATALOG))
    assert result is not None
    assert result.id == 118


async def test_resolve_instrument_base_asset_only():
    result = await resolve_instrument("BTC", FakeListInstruments(_CATALOG))
    assert result is not None
    assert result.id == 118


async def test_resolve_instrument_unknown_symbol_returns_none():
    result = await resolve_instrument("DOGE/USDT", FakeListInstruments(_CATALOG))
    assert result is None


class FakeManageAlerts:
    def __init__(self) -> None:
        self.created: list = []
        self.deleted: list[int] = []

    async def create(self, request):
        self.created.append(request)

        class _Dto:
            def model_dump(self, mode="json"):
                return {"id": 1, "instrument_id": request.instrument_id}

        return _Dto()

    async def delete(self, alert_id: int) -> None:
        self.deleted.append(alert_id)

    async def list_alerts(self):
        class _Dto:
            def model_dump(self, mode="json"):
                return {"alerts": []}

        return _Dto()


async def test_create_alert_resolves_symbol_and_calls_use_case():
    manage_alerts = FakeManageAlerts()
    instruments = FakeListInstruments(_CATALOG)

    result = await ex.exec_create_alert(
        instruments,
        manage_alerts,
        {"symbol": "BTC/USDT", "condition_type": "price_above", "threshold": 50000.0},
        user_id=1,
    )

    assert result["ok"] is True
    assert len(manage_alerts.created) == 1
    assert manage_alerts.created[0].instrument_id == 118
    assert manage_alerts.created[0].condition_type == "price_above"


async def test_create_alert_unknown_symbol_returns_error_without_calling_use_case():
    manage_alerts = FakeManageAlerts()
    instruments = FakeListInstruments(_CATALOG)

    result = await ex.exec_create_alert(
        instruments,
        manage_alerts,
        {"symbol": "DOGE/USDT", "condition_type": "price_above", "threshold": 1.0},
        user_id=1,
    )

    assert result["ok"] is False
    assert manage_alerts.created == []


async def test_delete_alert_calls_use_case():
    manage_alerts = FakeManageAlerts()

    result = await ex.exec_delete_alert(manage_alerts, {"alert_id": 7}, user_id=1)

    assert result["ok"] is True
    assert manage_alerts.deleted == [7]


class FakeManageSessions:
    def __init__(self) -> None:
        self.created: list = []
        self.stopped: list[int] = []

    async def create(self, request):
        self.created.append(request)

        class _Dto:
            def model_dump(self, mode="json"):
                return {"id": 1}

        return _Dto()

    async def stop(self, session_id: int):
        self.stopped.append(session_id)

        class _Dto:
            def model_dump(self, mode="json"):
                return {"id": session_id, "status": "stopped"}

        return _Dto()


async def test_create_paper_trading_session_resolves_symbol():
    manage_sessions = FakeManageSessions()
    instruments = FakeListInstruments(_CATALOG)

    result = await ex.exec_create_paper_trading_session(
        instruments, manage_sessions, {"symbol": "ETH/USDT", "timeframe": "1h"}, user_id=1
    )

    assert result["ok"] is True
    assert manage_sessions.created[0].instrument_id == 119
    assert manage_sessions.created[0].strategy.type == "sma_crossover"


async def test_stop_paper_trading_session_calls_use_case():
    manage_sessions = FakeManageSessions()

    result = await ex.exec_stop_paper_trading_session(manage_sessions, {"session_id": 3}, user_id=1)

    assert result["ok"] is True
    assert manage_sessions.stopped == [3]


class FakeUpdateSetting:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str, str]] = []

    async def execute(self, user_id: int, key: str, value: str):
        self.calls.append((user_id, key, value))

        class _Dto:
            def model_dump(self, mode="json"):
                return {"settings": {key: value}}

        return _Dto()


async def test_update_setting_rejects_non_allowlisted_key():
    update_setting = FakeUpdateSetting()

    result = await ex.exec_update_setting(
        update_setting, {"key": "admin_password", "value": "x"}, user_id=1
    )

    assert result["ok"] is False
    assert update_setting.calls == []


async def test_update_setting_allows_known_key():
    update_setting = FakeUpdateSetting()

    result = await ex.exec_update_setting(
        update_setting, {"key": "ai_temperature", "value": "0.5"}, user_id=1
    )

    assert result["ok"] is True
    assert update_setting.calls == [(1, "ai_temperature", "0.5")]


class FakeManageTraining:
    def __init__(self) -> None:
        self.started: list = []
        self.stopped: list = []

    async def start(self, timeframe: str, instrument_ids: list[int]):
        self.started.append((timeframe, instrument_ids))

        class _Dto:
            def model_dump(self, mode="json"):
                return {"sessions": []}

        return _Dto()

    async def stop(self, timeframe: str, instrument_ids: list[int]):
        self.stopped.append((timeframe, instrument_ids))

        class _Dto:
            def model_dump(self, mode="json"):
                return {"sessions": []}

        return _Dto()


async def test_start_training_resolves_symbol_and_calls_use_case():
    manage_training = FakeManageTraining()
    instruments = FakeListInstruments(_CATALOG)

    result = await ex.exec_start_training(
        instruments, manage_training, {"symbol": "BTC/USDT", "timeframe": "15m"}, user_id=1
    )

    assert result["ok"] is True
    assert manage_training.started == [("15m", [118])]


async def test_stop_training_resolves_symbol_and_calls_use_case():
    manage_training = FakeManageTraining()
    instruments = FakeListInstruments(_CATALOG)

    result = await ex.exec_stop_training(
        instruments, manage_training, {"symbol": "BTC/USDT", "timeframe": "15m"}, user_id=1
    )

    assert result["ok"] is True
    assert manage_training.stopped == [("15m", [118])]


class FakeOptimizeModel:
    def __init__(self) -> None:
        self.calls: list = []

    async def execute(self, request):
        self.calls.append(request)

        class _Dto:
            def model_dump(self, mode="json"):
                return {"best_params": {}}

        return _Dto()


async def test_optimize_model_hyperparameters_resolves_symbol():
    optimize_model = FakeOptimizeModel()
    instruments = FakeListInstruments(_CATALOG)

    result = await ex.exec_optimize_model_hyperparameters(
        instruments, optimize_model, {"symbol": "BTC/USDT", "timeframe": "15m"}, user_id=1
    )

    assert result["ok"] is True
    assert optimize_model.calls[0].instrument_id == 118
    assert optimize_model.calls[0].n_trials == 15


async def test_optimize_model_hyperparameters_unknown_symbol_errors():
    optimize_model = FakeOptimizeModel()
    instruments = FakeListInstruments(_CATALOG)

    result = await ex.exec_optimize_model_hyperparameters(
        instruments, optimize_model, {"symbol": "DOGE/USDT", "timeframe": "15m"}, user_id=1
    )

    assert result["ok"] is False
    assert optimize_model.calls == []


class FakeRaisingUseCase:
    async def execute(self, *args, **kwargs):
        raise RuntimeError("boom")


async def test_unexpected_exception_is_caught_and_returned_as_error():
    result = await ex.exec_get_risk_budget(FakeRaisingUseCase(), {}, user_id=1)

    assert result["ok"] is False
    assert "boom" in result["error"]

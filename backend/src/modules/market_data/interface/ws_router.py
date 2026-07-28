import asyncio
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.composition_root import get_ohlcv_use_case, token_provider
from src.modules.market_data.domain.value_objects import SUPPORTED_TIMEFRAMES, Timeframe
from src.shared.infrastructure.database import SessionLocal

router = APIRouter(tags=["market-data"])

_MIN_POLL_SECONDS = 1
_MAX_POLL_SECONDS = 15
_PUSH_WINDOW_CANDLES = 3


async def _fetch_latest(instrument_id: int, timeframe: str) -> list[dict]:
    async with SessionLocal() as session:
        use_case = get_ohlcv_use_case(session)
        seconds = Timeframe(timeframe).seconds
        end = datetime.now(timezone.utc)
        start = end - timedelta(seconds=seconds * (_PUSH_WINDOW_CANDLES + 1))
        response = await use_case.execute(instrument_id, timeframe, start, end, 50)
        return [
            {
                "open_time": c.open_time.isoformat().replace("+00:00", "Z"),
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in response.candles[-_PUSH_WINDOW_CANDLES:]
        ]


@router.websocket("/ws/market-data")
async def market_data_stream(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if token is None or token_provider.verify(token) is None:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    instrument_id: int | None = None
    timeframe: str | None = None
    poll_seconds = _MIN_POLL_SECONDS

    try:
        while True:
            timeout = poll_seconds if instrument_id else None
            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(), timeout=timeout
                )
                message = json.loads(raw)
                if (
                    message.get("type") == "subscribe"
                    and message.get("timeframe") in SUPPORTED_TIMEFRAMES
                ):
                    instrument_id = int(message["instrument_id"])
                    timeframe = str(message["timeframe"])
                    poll_seconds = min(
                        max(Timeframe(timeframe).seconds, _MIN_POLL_SECONDS),
                        _MAX_POLL_SECONDS,
                    )
                continue
            except asyncio.TimeoutError:
                pass
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

            if instrument_id is None or timeframe is None:
                continue
            try:
                candles = await _fetch_latest(instrument_id, timeframe)
                await websocket.send_json(
                    {
                        "type": "candles",
                        "instrument_id": instrument_id,
                        "timeframe": timeframe,
                        "candles": candles,
                    }
                )
            except WebSocketDisconnect:
                raise
            except Exception:
                # Transient upstream failure (exchange/db): keep the socket
                # alive, the next poll retries.
                await asyncio.sleep(poll_seconds)
    except WebSocketDisconnect:
        pass

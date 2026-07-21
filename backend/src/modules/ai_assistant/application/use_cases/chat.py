from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from src.modules.market_data.application.use_cases.list_instruments import (
    ListInstrumentsUseCase,
)
from src.modules.technical_analysis.application import service as ta
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.shared.kernel.errors import AppError


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    model: str
    context_note: str


_SYSTEM_PROMPT = (
    "Tu es l'assistant d'IndraQuant, une plateforme personnelle d'aide à la "
    "décision pour les marchés financiers. Tu réponds en français, de façon "
    "concise et honnête. Règles absolues : tu ne donnes jamais de certitude "
    "sur l'évolution future des prix, uniquement des observations et des "
    "probabilités ; tu rappelles que rien n'est un conseil d'investissement ; "
    "tu t'appuies sur le contexte de marché fourni ci-dessous quand c'est "
    "pertinent.\n\nContexte de marché actuel :\n{context}"
)


class ChatUseCase:
    def __init__(
        self,
        instruments: ListInstrumentsUseCase,
        ohlcv: OhlcvProvider,
        ollama_chat,
    ) -> None:
        self._instruments = instruments
        self._ohlcv = ohlcv
        self._ollama_chat = ollama_chat

    def execute(self, request: ChatRequest) -> ChatResponse:
        context = self._market_context()
        messages = (
            [{"role": "system", "content": _SYSTEM_PROMPT.format(context=context)}]
            + [m.model_dump() for m in request.history[-8:]]
            + [{"role": "user", "content": request.message}]
        )
        try:
            reply = self._ollama_chat(messages)
        except Exception as error:
            raise AppError(
                "assistant_unavailable",
                f"Assistant indisponible (Ollama) : {error}",
                http_status=502,
            )
        return ChatResponse(
            reply=reply,
            model="llama3.1:8b (Ollama, local)",
            context_note=(
                "L'assistant reçoit un instantané des instruments suivis "
                "(dernier prix, RSI 14 en 1h). Il ne donne pas de conseil "
                "d'investissement."
            ),
        )

    def _market_context(self) -> str:
        lines = []
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=60)
        for instrument in self._instruments.execute().instruments[:6]:
            try:
                candles = self._ohlcv.execute(
                    instrument.id, "1h", start, end, 500
                ).candles
            except Exception:
                continue
            if not candles:
                continue
            closes = [c.close for c in candles]
            rsi = ta.rsi(closes, 14)[-1]
            lines.append(
                f"- {instrument.symbol} ({instrument.exchange}) : dernier prix "
                f"{closes[-1]:.2f}, RSI14 1h "
                f"{f'{rsi:.1f}' if rsi is not None else 'n/d'}"
            )
        return "\n".join(lines) if lines else "(données indisponibles)"

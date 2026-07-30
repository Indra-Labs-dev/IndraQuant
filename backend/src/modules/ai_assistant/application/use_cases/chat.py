from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from src.modules.ai_assistant.domain.repositories import ChatRepository, MemoryRepository
from src.modules.market_data.application.use_cases.list_instruments import (
    ListInstrumentsUseCase,
)
from src.modules.settings.domain.repositories import SettingsRepository
from src.modules.technical_analysis.application import service as ta
from src.modules.technical_analysis.application.ports import OhlcvProvider
from src.shared.kernel.errors import AppError

# How many persisted messages are loaded to reconstruct "l'historique complet"
# for the frontend/prompt; still truncated to the last 8 for the Ollama call
# itself (context window).
_HISTORY_LIMIT = 200
_PROMPT_HISTORY_MESSAGES = 8

# User-configurable via Settings (ai_temperature/ai_max_tokens) — same knobs
# exposed in the frontend Settings page, clamped here so an invalid/extreme
# stored value can never make the model unusable.
_DEFAULT_TEMPERATURE = 0.3
_MIN_TEMPERATURE, _MAX_TEMPERATURE = 0.0, 1.0
# qwen2.5-coder supports up to a 32K-token context window (model card), so
# the reply-length cap can go as high as that same ceiling.
_DEFAULT_MAX_TOKENS = 512
_MIN_MAX_TOKENS, _MAX_MAX_TOKENS = 64, 32_768


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str


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
    "\n\nMémoire (faits retenus des échanges précédents) :\n{memory}"
)


class ChatUseCase:
    def __init__(
        self,
        instruments: ListInstrumentsUseCase,
        ohlcv: OhlcvProvider,
        ollama_chat,
        chat_repository: ChatRepository,
        memory_repository: MemoryRepository,
        extract_memory_facts,
        settings_repository: SettingsRepository,
    ) -> None:
        self._instruments = instruments
        self._ohlcv = ohlcv
        self._ollama_chat = ollama_chat
        self._chat_repository = chat_repository
        self._memory_repository = memory_repository
        self._extract_memory_facts = extract_memory_facts
        self._settings_repository = settings_repository

    async def execute(self, user_id: int, request: ChatRequest) -> ChatResponse:
        context = await self._market_context()
        known_facts = [f.content for f in await self._memory_repository.list_facts(user_id)]
        memory_block = "\n".join(f"- {f}" for f in known_facts) or "(aucun pour l'instant)"
        history = await self._chat_repository.list_recent(user_id, _HISTORY_LIMIT)
        messages = (
            [
                {
                    "role": "system",
                    "content": _SYSTEM_PROMPT.format(context=context, memory=memory_block),
                }
            ]
            + [
                {"role": h.role, "content": h.content}
                for h in history[-_PROMPT_HISTORY_MESSAGES:]
            ]
            + [{"role": "user", "content": request.message}]
        )
        temperature, max_tokens = await self._chat_parameters(user_id)
        try:
            reply = self._ollama_chat(
                messages, temperature=temperature, num_predict=max_tokens
            )
        except Exception as error:
            raise AppError(
                "assistant_unavailable",
                f"Assistant indisponible (Ollama) : {error}",
                http_status=502,
            )

        await self._chat_repository.add_message(user_id, "user", request.message)
        await self._chat_repository.add_message(user_id, "assistant", reply)

        try:
            updated_facts = self._extract_memory_facts(known_facts, request.message, reply)
            await self._memory_repository.replace_facts(user_id, updated_facts)
        except Exception:
            pass

        return ChatResponse(
            reply=reply,
            model="qwen2.5-coder:3b (Ollama, local)",
            context_note=(
                "L'assistant reçoit un instantané des instruments suivis "
                "(dernier prix, RSI 14 en 1h). Il ne donne pas de conseil "
                "d'investissement."
            ),
        )

    async def _chat_parameters(self, user_id: int) -> tuple[float, int]:
        settings = {s.key: s.value for s in await self._settings_repository.get_all(user_id)}
        temperature = _DEFAULT_TEMPERATURE
        max_tokens = _DEFAULT_MAX_TOKENS
        try:
            if "ai_temperature" in settings:
                temperature = min(
                    _MAX_TEMPERATURE, max(_MIN_TEMPERATURE, float(settings["ai_temperature"]))
                )
        except ValueError:
            pass
        try:
            if "ai_max_tokens" in settings:
                max_tokens = min(
                    _MAX_MAX_TOKENS, max(_MIN_MAX_TOKENS, int(settings["ai_max_tokens"]))
                )
        except ValueError:
            pass
        return temperature, max_tokens

    async def _market_context(self) -> str:
        lines = []
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=60)
        instruments_response = await self._instruments.execute()
        for instrument in instruments_response.instruments[:6]:
            try:
                response = await self._ohlcv.execute(
                    instrument.id, "1h", start, end, 500
                )
                candles = response.candles
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

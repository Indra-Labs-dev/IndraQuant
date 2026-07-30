from datetime import datetime, timezone

import pytest

from src.modules.ai_assistant.application.use_cases.chat import (
    ChatRequest,
    ChatUseCase,
)
from src.modules.ai_assistant.application.use_cases.get_chat_history import (
    GetChatHistoryUseCase,
)
from src.modules.ai_assistant.application.use_cases.manage_memory import (
    ClearMemoryUseCase,
    GetMemoryUseCase,
)
from src.modules.ai_assistant.domain.entities import ChatMessageRecord, MemoryFact
from src.modules.market_data.application.dto import InstrumentsResponse
from src.modules.settings.domain.entities import Setting
from src.shared.kernel.errors import AppError


class FakeChatRepository:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str, str]] = []

    async def add_message(self, user_id: int, role: str, content: str) -> None:
        self.messages.append((user_id, role, content))

    async def list_recent(self, user_id: int, limit: int) -> list[ChatMessageRecord]:
        mine = [
            ChatMessageRecord(role=role, content=content, created_at=datetime.now(timezone.utc))
            for uid, role, content in self.messages
            if uid == user_id
        ]
        return mine[-limit:]


class FakeMemoryRepository:
    def __init__(self, initial: list[str] | None = None) -> None:
        self._facts: dict[int, list[str]] = {1: list(initial)} if initial else {}

    async def list_facts(self, user_id: int) -> list[MemoryFact]:
        return [MemoryFact(content=c) for c in self._facts.get(user_id, [])]

    async def replace_facts(self, user_id: int, facts: list[str]) -> None:
        self._facts[user_id] = list(facts)


class FakeSettingsRepository:
    def __init__(self, initial: dict[str, str] | None = None) -> None:
        self._data: dict[tuple[int, str], str] = {
            (1, key): value for key, value in (initial or {}).items()
        }

    async def get_all(self, user_id: int) -> list[Setting]:
        return [
            Setting(key=key, value=value)
            for (uid, key), value in self._data.items()
            if uid == user_id
        ]

    async def upsert(self, user_id: int, key: str, value: str) -> Setting:
        self._data[(user_id, key)] = value
        return Setting(key=key, value=value)


class FakeListInstruments:
    async def execute(self, *args, **kwargs) -> InstrumentsResponse:
        return InstrumentsResponse(instruments=[])


def _make_ollama_chat(captured: list, reply: str = "reponse"):
    def _chat(messages: list[dict], temperature: float = 0.3, num_predict: int | None = None) -> str:
        captured.append({"messages": messages, "temperature": temperature, "num_predict": num_predict})
        return reply

    return _chat


def _keep_facts_unchanged(known_facts, user_message, assistant_reply):
    return known_facts


async def test_execute_persists_user_and_assistant_messages_after_reply():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository()
    use_case = ChatUseCase(
        FakeListInstruments(),
        None,
        _make_ollama_chat([], "Bonjour"),
        chat_repo,
        memory_repo,
        _keep_facts_unchanged,
        FakeSettingsRepository(),
    )

    response = await use_case.execute(1, ChatRequest(message="Salut"))

    assert response.reply == "Bonjour"
    assert chat_repo.messages == [(1, "user", "Salut"), (1, "assistant", "Bonjour")]


async def test_only_last_eight_persisted_messages_are_sent_to_ollama():
    chat_repo = FakeChatRepository()
    for i in range(10):
        await chat_repo.add_message(1, "user" if i % 2 == 0 else "assistant", f"msg-{i}")
    memory_repo = FakeMemoryRepository()
    captured: list = []
    use_case = ChatUseCase(
        FakeListInstruments(),
        None,
        _make_ollama_chat(captured),
        chat_repo,
        memory_repo,
        _keep_facts_unchanged,
        FakeSettingsRepository(),
    )

    await use_case.execute(1, ChatRequest(message="nouveau"))

    sent_messages = captured[0]["messages"]
    # system prompt + last 8 persisted messages + the new user message.
    assert len(sent_messages) == 1 + 8 + 1
    history_contents = [m["content"] for m in sent_messages[1:-1]]
    assert history_contents == [f"msg-{i}" for i in range(2, 10)]


async def test_known_memory_facts_are_injected_into_system_prompt():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository(initial=["Préfère les paires crypto majeures"])
    captured: list = []
    use_case = ChatUseCase(
        FakeListInstruments(),
        None,
        _make_ollama_chat(captured),
        chat_repo,
        memory_repo,
        _keep_facts_unchanged,
        FakeSettingsRepository(),
    )

    await use_case.execute(1, ChatRequest(message="salut"))

    system_message = captured[0]["messages"][0]["content"]
    assert "Préfère les paires crypto majeures" in system_message


async def test_fact_extraction_failure_does_not_break_chat_response():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository(initial=["fait existant"])

    def failing_extract(known_facts, user_message, assistant_reply):
        raise RuntimeError("ollama indisponible")

    use_case = ChatUseCase(
        FakeListInstruments(),
        None,
        _make_ollama_chat([], "ok"),
        chat_repo,
        memory_repo,
        failing_extract,
        FakeSettingsRepository(),
    )

    response = await use_case.execute(1, ChatRequest(message="salut"))

    assert response.reply == "ok"
    facts = await memory_repo.list_facts(1)
    assert [f.content for f in facts] == ["fait existant"]


async def test_ollama_failure_raises_and_persists_nothing():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository()

    def failing_chat(messages: list[dict], temperature: float = 0.3, num_predict: int | None = None) -> str:
        raise RuntimeError("connection refused")

    use_case = ChatUseCase(
        FakeListInstruments(),
        None,
        failing_chat,
        chat_repo,
        memory_repo,
        _keep_facts_unchanged,
        FakeSettingsRepository(),
    )

    with pytest.raises(AppError):
        await use_case.execute(1, ChatRequest(message="salut"))

    assert chat_repo.messages == []


async def test_default_temperature_and_max_tokens_are_used_when_no_settings_saved():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository()
    captured: list = []
    use_case = ChatUseCase(
        FakeListInstruments(),
        None,
        _make_ollama_chat(captured),
        chat_repo,
        memory_repo,
        _keep_facts_unchanged,
        FakeSettingsRepository(),
    )

    await use_case.execute(1, ChatRequest(message="salut"))

    assert captured[0]["temperature"] == 0.3
    assert captured[0]["num_predict"] == 512


async def test_saved_temperature_and_max_tokens_settings_are_applied():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository()
    captured: list = []
    settings_repo = FakeSettingsRepository({"ai_temperature": "0.8", "ai_max_tokens": "1024"})
    use_case = ChatUseCase(
        FakeListInstruments(),
        None,
        _make_ollama_chat(captured),
        chat_repo,
        memory_repo,
        _keep_facts_unchanged,
        settings_repo,
    )

    await use_case.execute(1, ChatRequest(message="salut"))

    assert captured[0]["temperature"] == 0.8
    assert captured[0]["num_predict"] == 1024


async def test_out_of_range_settings_are_clamped_instead_of_rejected():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository()
    captured: list = []
    settings_repo = FakeSettingsRepository({"ai_temperature": "5", "ai_max_tokens": "999999"})
    use_case = ChatUseCase(
        FakeListInstruments(),
        None,
        _make_ollama_chat(captured),
        chat_repo,
        memory_repo,
        _keep_facts_unchanged,
        settings_repo,
    )

    await use_case.execute(1, ChatRequest(message="salut"))

    assert captured[0]["temperature"] == 1.0
    assert captured[0]["num_predict"] == 32768


async def test_get_chat_history_returns_persisted_messages_for_this_user_in_order():
    chat_repo = FakeChatRepository()
    await chat_repo.add_message(1, "user", "un")
    await chat_repo.add_message(1, "assistant", "deux")
    await chat_repo.add_message(2, "user", "autre utilisateur")

    response = await GetChatHistoryUseCase(chat_repo).execute(1)

    assert [m.content for m in response.messages] == ["un", "deux"]


async def test_get_memory_use_case_returns_persisted_facts():
    memory_repo = FakeMemoryRepository(initial=["fait 1", "fait 2"])

    response = await GetMemoryUseCase(memory_repo).execute(1)

    assert response.facts == ["fait 1", "fait 2"]


async def test_clear_memory_use_case_empties_facts():
    memory_repo = FakeMemoryRepository(initial=["fait 1"])

    response = await ClearMemoryUseCase(memory_repo).execute(1)

    assert response.facts == []
    remaining = await memory_repo.list_facts(1)
    assert remaining == []

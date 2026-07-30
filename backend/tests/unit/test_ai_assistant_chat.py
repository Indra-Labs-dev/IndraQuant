from datetime import datetime, timezone

import pytest

from src.modules.ai_assistant.application.tool_calling_loop import ToolCallingLoop
from src.modules.ai_assistant.application.tools.registry import ToolRegistry
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
from src.modules.ai_assistant.domain.entities import (
    ChatMessageRecord,
    Conversation,
    MemoryFact,
)
from src.modules.market_data.application.dto import InstrumentsResponse
from src.modules.settings.domain.entities import Setting
from src.shared.kernel.errors import AppError

_EMPTY_TOOL_REGISTRY = ToolRegistry(specs={}, dispatch={})


class FakeChatRepository:
    def __init__(self) -> None:
        self.messages: list[tuple[int, int, str, str]] = []

    async def add_message(
        self, user_id: int, conversation_id: int, role: str, content: str
    ) -> None:
        self.messages.append((user_id, conversation_id, role, content))

    async def list_recent(
        self, user_id: int, conversation_id: int, limit: int
    ) -> list[ChatMessageRecord]:
        mine = [
            ChatMessageRecord(role=role, content=content, created_at=datetime.now(timezone.utc))
            for uid, cid, role, content in self.messages
            if uid == user_id and cid == conversation_id
        ]
        return mine[-limit:]


class FakeConversationRepository:
    def __init__(self) -> None:
        self._conversations: dict[int, tuple[int, str | None]] = {}
        self._next_id = 1

    async def list_conversations(self, user_id: int) -> list[Conversation]:
        return [
            Conversation(id=cid, title=title, updated_at=datetime.now(timezone.utc))
            for cid, (uid, title) in self._conversations.items()
            if uid == user_id
        ]

    async def create_conversation(self, user_id: int, title: str) -> Conversation:
        conversation_id = self._next_id
        self._next_id += 1
        self._conversations[conversation_id] = (user_id, title)
        return Conversation(
            id=conversation_id, title=title, updated_at=datetime.now(timezone.utc)
        )


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


class _FakeToolResult:
    """Mimics `OllamaClient.ToolCallResult` with `tool_call=None` — i.e. a
    normal text reply, never a tool call. Existing chat tests only exercise
    the plain conversational path, not tool-calling itself (see
    test_ai_assistant_tool_calling_loop.py for that)."""

    def __init__(self, content: str) -> None:
        self.content = content
        self.tool_call = None


def _make_tools_loop(captured: list, reply: str = "reponse") -> ToolCallingLoop:
    def _chat_with_tools(messages, tools, temperature=0.3, num_predict=None):
        captured.append(
            {
                "messages": messages,
                "tools": tools,
                "temperature": temperature,
                "num_predict": num_predict,
            }
        )
        return _FakeToolResult(reply)

    return ToolCallingLoop(_chat_with_tools, _EMPTY_TOOL_REGISTRY)


def _make_failing_tools_loop() -> ToolCallingLoop:
    def _failing(messages, tools, temperature=0.3, num_predict=None):
        raise RuntimeError("connection refused")

    return ToolCallingLoop(_failing, _EMPTY_TOOL_REGISTRY)


def _keep_facts_unchanged(known_facts, user_message, assistant_reply):
    return known_facts


def _make_use_case(
    chat_repo,
    memory_repo,
    tools_loop,
    settings_repo=None,
    conversation_repo=None,
    extract_facts=_keep_facts_unchanged,
) -> ChatUseCase:
    return ChatUseCase(
        FakeListInstruments(),
        None,
        tools_loop,
        chat_repo,
        memory_repo,
        extract_facts,
        settings_repo or FakeSettingsRepository(),
        conversation_repo or FakeConversationRepository(),
    )


async def test_execute_persists_user_and_assistant_messages_after_reply():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository()
    use_case = _make_use_case(chat_repo, memory_repo, _make_tools_loop([], "Bonjour"))

    response = await use_case.execute(1, ChatRequest(message="Salut"))

    assert response.reply == "Bonjour"
    assert response.tools_invoked == []
    assert chat_repo.messages == [
        (1, response.conversation_id, "user", "Salut"),
        (1, response.conversation_id, "assistant", "Bonjour"),
    ]


async def test_new_conversation_is_created_with_title_from_first_message():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository()
    conversation_repo = FakeConversationRepository()
    use_case = _make_use_case(
        chat_repo, memory_repo, _make_tools_loop([]), conversation_repo=conversation_repo
    )

    response = await use_case.execute(
        1, ChatRequest(message="Quelle est la tendance du BTC ?")
    )

    conversations = await conversation_repo.list_conversations(1)
    assert len(conversations) == 1
    assert conversations[0].id == response.conversation_id
    assert conversations[0].title == "Quelle est la tendance du BTC ?"


async def test_existing_conversation_id_is_reused_without_creating_a_new_one():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository()
    conversation_repo = FakeConversationRepository()
    existing = await conversation_repo.create_conversation(1, title="Ancienne conversation")
    use_case = _make_use_case(
        chat_repo, memory_repo, _make_tools_loop([]), conversation_repo=conversation_repo
    )

    response = await use_case.execute(
        1, ChatRequest(message="suite", conversation_id=existing.id)
    )

    assert response.conversation_id == existing.id
    assert len(await conversation_repo.list_conversations(1)) == 1


async def test_two_conversations_for_the_same_user_do_not_mix_history():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository()
    conversation_repo = FakeConversationRepository()
    captured: list = []
    use_case = _make_use_case(
        chat_repo,
        memory_repo,
        _make_tools_loop(captured, "reponse A"),
        conversation_repo=conversation_repo,
    )

    response_a = await use_case.execute(1, ChatRequest(message="Bonjour A"))
    response_b = await use_case.execute(1, ChatRequest(message="Bonjour B"))

    assert response_a.conversation_id != response_b.conversation_id
    history_a = await chat_repo.list_recent(1, response_a.conversation_id, 200)
    history_b = await chat_repo.list_recent(1, response_b.conversation_id, 200)
    assert [m.content for m in history_a] == ["Bonjour A", "reponse A"]
    assert [m.content for m in history_b] == ["Bonjour B", "reponse A"]


async def test_only_last_eight_persisted_messages_are_sent_to_ollama():
    chat_repo = FakeChatRepository()
    conversation_repo = FakeConversationRepository()
    conversation = await conversation_repo.create_conversation(1, title="fil existant")
    for i in range(10):
        await chat_repo.add_message(
            1, conversation.id, "user" if i % 2 == 0 else "assistant", f"msg-{i}"
        )
    memory_repo = FakeMemoryRepository()
    captured: list = []
    use_case = _make_use_case(
        chat_repo, memory_repo, _make_tools_loop(captured), conversation_repo=conversation_repo
    )

    await use_case.execute(1, ChatRequest(message="nouveau", conversation_id=conversation.id))

    sent_messages = captured[0]["messages"]
    # system prompt + last 8 persisted messages + the new user message.
    assert len(sent_messages) == 1 + 8 + 1
    history_contents = [m["content"] for m in sent_messages[1:-1]]
    assert history_contents == [f"msg-{i}" for i in range(2, 10)]


async def test_known_memory_facts_are_injected_into_system_prompt():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository(initial=["Préfère les paires crypto majeures"])
    captured: list = []
    use_case = _make_use_case(chat_repo, memory_repo, _make_tools_loop(captured))

    await use_case.execute(1, ChatRequest(message="salut"))

    system_message = captured[0]["messages"][0]["content"]
    assert "Préfère les paires crypto majeures" in system_message


async def test_fact_extraction_failure_does_not_break_chat_response():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository(initial=["fait existant"])

    def failing_extract(known_facts, user_message, assistant_reply):
        raise RuntimeError("ollama indisponible")

    use_case = _make_use_case(
        chat_repo, memory_repo, _make_tools_loop([], "ok"), extract_facts=failing_extract
    )

    response = await use_case.execute(1, ChatRequest(message="salut"))

    assert response.reply == "ok"
    facts = await memory_repo.list_facts(1)
    assert [f.content for f in facts] == ["fait existant"]


async def test_ollama_failure_raises_and_persists_nothing():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository()
    use_case = _make_use_case(chat_repo, memory_repo, _make_failing_tools_loop())

    with pytest.raises(AppError):
        await use_case.execute(1, ChatRequest(message="salut"))

    assert chat_repo.messages == []


async def test_default_temperature_and_max_tokens_are_used_when_no_settings_saved():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository()
    captured: list = []
    use_case = _make_use_case(chat_repo, memory_repo, _make_tools_loop(captured))

    await use_case.execute(1, ChatRequest(message="salut"))

    assert captured[0]["temperature"] == 0.3
    assert captured[0]["num_predict"] == 512


async def test_saved_temperature_and_max_tokens_settings_are_applied():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository()
    captured: list = []
    settings_repo = FakeSettingsRepository({"ai_temperature": "0.8", "ai_max_tokens": "1024"})
    use_case = _make_use_case(
        chat_repo, memory_repo, _make_tools_loop(captured), settings_repo=settings_repo
    )

    await use_case.execute(1, ChatRequest(message="salut"))

    assert captured[0]["temperature"] == 0.8
    assert captured[0]["num_predict"] == 1024


async def test_out_of_range_settings_are_clamped_instead_of_rejected():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository()
    captured: list = []
    settings_repo = FakeSettingsRepository({"ai_temperature": "5", "ai_max_tokens": "999999"})
    use_case = _make_use_case(
        chat_repo, memory_repo, _make_tools_loop(captured), settings_repo=settings_repo
    )

    await use_case.execute(1, ChatRequest(message="salut"))

    assert captured[0]["temperature"] == 1.0
    assert captured[0]["num_predict"] == 32768


async def test_ai_tools_enabled_false_skips_tools_array():
    chat_repo = FakeChatRepository()
    memory_repo = FakeMemoryRepository()
    captured: list = []
    settings_repo = FakeSettingsRepository({"ai_tools_enabled": "false"})
    use_case = _make_use_case(
        chat_repo, memory_repo, _make_tools_loop(captured), settings_repo=settings_repo
    )

    await use_case.execute(1, ChatRequest(message="salut"))

    assert captured[0]["tools"] == []


async def test_get_chat_history_returns_persisted_messages_for_this_conversation_in_order():
    chat_repo = FakeChatRepository()
    await chat_repo.add_message(1, 10, "user", "un")
    await chat_repo.add_message(1, 10, "assistant", "deux")
    await chat_repo.add_message(1, 11, "user", "autre conversation")

    response = await GetChatHistoryUseCase(chat_repo).execute(1, 10)

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

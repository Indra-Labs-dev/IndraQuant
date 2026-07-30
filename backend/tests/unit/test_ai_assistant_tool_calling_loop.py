from src.modules.ai_assistant.application.tool_calling_loop import ToolCallingLoop
from src.modules.ai_assistant.application.tools.registry import ToolRegistry


class _Result:
    def __init__(self, content: str = "", tool_call: dict | None = None) -> None:
        self.content = content
        self.tool_call = tool_call


def _scripted_chat_with_tools(results: list[_Result], calls: list):
    iterator = iter(results)

    def _chat_with_tools(messages, tools, temperature=0.3, num_predict=None):
        calls.append({"messages": list(messages), "tools": tools})
        return next(iterator)

    return _chat_with_tools


async def _fake_get_price(args: dict, user_id: int) -> dict:
    return {"ok": True, "symbol": args.get("symbol"), "price": 42_000.0}


def _registry_with(name: str, dispatch_fn) -> ToolRegistry:
    return ToolRegistry(specs={}, dispatch={name: dispatch_fn})


async def test_valid_tool_call_then_final_answer_is_used():
    calls: list = []
    results = [
        _Result(tool_call={"name": "get_price", "arguments": {"symbol": "BTC/USDT"}}),
        _Result(content="Le prix du BTC/USDT est de 42000 USD."),
    ]
    loop = ToolCallingLoop(
        _scripted_chat_with_tools(results, calls), _registry_with("get_price", _fake_get_price)
    )

    result = await loop.run(
        [{"role": "system", "content": "sys"}, {"role": "user", "content": "prix ?"}],
        user_id=1,
        tools_enabled=True,
        temperature=0.3,
        max_tokens=512,
    )

    assert result.reply == "Le prix du BTC/USDT est de 42000 USD."
    assert result.tools_invoked == ["get_price"]
    assert len(calls) == 2
    second_call_messages = calls[1]["messages"]
    assert second_call_messages[-2]["role"] == "assistant"
    assert second_call_messages[-1]["role"] == "tool"
    assert second_call_messages[-1]["name"] == "get_price"
    assert "42000.0" in second_call_messages[-1]["content"] or "42000" in second_call_messages[-1]["content"]


async def test_unknown_tool_name_falls_back_to_plain_answer_without_tools():
    calls: list = []
    results = [
        _Result(tool_call={"name": "greeting", "arguments": {}}),
        _Result(content="Bonjour ! Comment puis-je vous aider ?"),
    ]
    loop = ToolCallingLoop(_scripted_chat_with_tools(results, calls), ToolRegistry(specs={}, dispatch={}))

    result = await loop.run(
        [{"role": "system", "content": "sys"}, {"role": "user", "content": "salut"}],
        user_id=1,
        tools_enabled=True,
        temperature=0.3,
        max_tokens=512,
    )

    assert result.reply == "Bonjour ! Comment puis-je vous aider ?"
    assert result.tools_invoked == []
    assert len(calls) == 2
    assert calls[1]["tools"] == []
    # No raw JSON ever surfaces as the reply.
    assert "{" not in result.reply


async def test_hallucinated_json_data_object_never_reaches_the_user():
    # Regression test: observed live — after a valid `list_alerts` tool
    # round-trip, the model's "final" no-tools answer was a JSON object
    # unrelated to any tool call (e.g. a hallucinated alert record), which
    # `_parse_tool_call` correctly leaves as `tool_call=None` (it isn't
    # `{"name", "arguments"}`) but is still not natural language.
    calls: list = []
    results = [
        _Result(tool_call={"name": "list_alerts", "arguments": {}}),
        _Result(content='{"alert_id": 12345, "symbol": "BTC/USDT", "threshold": 60000}'),
    ]
    loop = ToolCallingLoop(
        _scripted_chat_with_tools(results, calls), _registry_with("list_alerts", _fake_get_price)
    )

    result = await loop.run(
        [{"role": "system", "content": "sys"}, {"role": "user", "content": "mes alertes ?"}],
        user_id=1,
        tools_enabled=True,
        temperature=0.3,
        max_tokens=512,
    )

    assert "{" not in result.reply
    assert "alert_id" not in result.reply
    assert result.tools_invoked == ["list_alerts"]


async def test_tool_execution_error_is_fed_back_as_tool_message_not_raised():
    calls: list = []

    async def _failing_tool(args: dict, user_id: int) -> dict:
        return {"ok": False, "error": "instrument introuvable : XYZ"}

    results = [
        _Result(tool_call={"name": "get_price", "arguments": {"symbol": "XYZ"}}),
        _Result(content="Je n'ai pas trouvé cet instrument."),
    ]
    loop = ToolCallingLoop(
        _scripted_chat_with_tools(results, calls), _registry_with("get_price", _failing_tool)
    )

    result = await loop.run(
        [{"role": "system", "content": "sys"}, {"role": "user", "content": "prix XYZ"}],
        user_id=1,
        tools_enabled=True,
        temperature=0.3,
        max_tokens=512,
    )

    assert result.reply == "Je n'ai pas trouvé cet instrument."
    tool_message = calls[1]["messages"][-1]
    assert tool_message["role"] == "tool"
    assert "introuvable" in tool_message["content"]


async def test_loop_is_bounded_even_if_model_always_requests_a_tool():
    # Regression test: a real ToolCallResult always carries the raw JSON in
    # `.content` alongside the parsed `.tool_call` (content is what gets
    # parsed FROM) — a fake that leaves `.content` empty when `.tool_call`
    # is set doesn't reproduce the real failure mode, where even the forced
    # final no-tools call can still come back JSON-shaped.
    calls: list = []
    tool_call = {"name": "get_price", "arguments": {"symbol": "BTC/USDT"}}

    def _always_tool_call(messages, tools, temperature=0.3, num_predict=None):
        calls.append({"messages": list(messages), "tools": tools})
        return _Result(content='{"name": "get_price", "arguments": {"symbol": "BTC/USDT"}}', tool_call=tool_call)

    loop = ToolCallingLoop(_always_tool_call, _registry_with("get_price", _fake_get_price))

    result = await loop.run(
        [{"role": "system", "content": "sys"}, {"role": "user", "content": "prix ?"}],
        user_id=1,
        tools_enabled=True,
        temperature=0.3,
        max_tokens=512,
    )

    # 4 iterations (each requesting a tool) + 1 forced final no-tools call.
    assert len(calls) == 5
    assert calls[-1]["tools"] == []
    assert result.tools_invoked == ["get_price"] * 4
    # Even though the forced final call still came back JSON-shaped, the
    # user must never see raw JSON.
    assert "{" not in result.reply
    assert "name" not in result.reply


async def test_tools_disabled_setting_skips_tools_array_entirely():
    calls: list = []
    results = [_Result(content="Bonjour, sans outils.")]
    loop = ToolCallingLoop(_scripted_chat_with_tools(results, calls), ToolRegistry(specs={}, dispatch={}))

    result = await loop.run(
        [{"role": "system", "content": "sys"}, {"role": "user", "content": "salut"}],
        user_id=1,
        tools_enabled=False,
        temperature=0.3,
        max_tokens=512,
    )

    assert len(calls) == 1
    assert calls[0]["tools"] == []
    assert result.reply == "Bonjour, sans outils."
    assert result.tools_invoked == []

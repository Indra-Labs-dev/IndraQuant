from unittest.mock import MagicMock, patch

from src.modules.sentiment_analysis.infrastructure.ollama_client import (
    OllamaClient,
    _parse_tool_call,
)


def test_parse_tool_call_plain_json():
    parsed = _parse_tool_call('{"name": "get_price", "arguments": {"symbol": "BTC/USDT"}}')
    assert parsed == {"name": "get_price", "arguments": {"symbol": "BTC/USDT"}}


def test_parse_tool_call_fenced_json():
    content = '```json\n{"name": "predict_direction", "arguments": {"symbol": "BTC/USDT", "timeframe": "1h"}}\n```'
    parsed = _parse_tool_call(content)
    assert parsed == {
        "name": "predict_direction",
        "arguments": {"symbol": "BTC/USDT", "timeframe": "1h"},
    }


def test_parse_tool_call_plain_text_is_not_a_tool_call():
    assert _parse_tool_call("Bonjour, comment puis-je vous aider ?") is None


def test_parse_tool_call_malformed_json_does_not_raise():
    assert _parse_tool_call("{invalid json") is None


def test_parse_tool_call_missing_name_is_not_a_tool_call():
    assert _parse_tool_call('{"arguments": {"symbol": "BTC/USDT"}}') is None


def test_parse_tool_call_empty_content_is_not_a_tool_call():
    assert _parse_tool_call("") is None


def _mock_response(content: str) -> MagicMock:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"message": {"role": "assistant", "content": content}}
    return response


def test_chat_with_tools_returns_parsed_tool_call():
    with patch("httpx.post", return_value=_mock_response(
        '{"name": "get_price", "arguments": {"symbol": "BTC/USDT"}}'
    )) as mock_post:
        result = OllamaClient().chat_with_tools(
            [{"role": "user", "content": "prix ?"}],
            tools=[{"type": "function", "function": {"name": "get_price"}}],
            temperature=0.5,
            num_predict=256,
        )

    assert result.tool_call == {"name": "get_price", "arguments": {"symbol": "BTC/USDT"}}
    sent_payload = mock_post.call_args.kwargs["json"]
    assert sent_payload["tools"] == [{"type": "function", "function": {"name": "get_price"}}]
    assert sent_payload["options"] == {"temperature": 0.5, "num_predict": 256}


def test_chat_with_tools_returns_plain_content_when_no_tool_call():
    with patch("httpx.post", return_value=_mock_response("Bonjour !")):
        result = OllamaClient().chat_with_tools(
            [{"role": "user", "content": "salut"}], tools=[]
        )

    assert result.content == "Bonjour !"
    assert result.tool_call is None

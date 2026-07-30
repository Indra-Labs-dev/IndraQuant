import json
import re
from dataclasses import dataclass, field

from src.modules.ai_assistant.application.tools.registry import ToolRegistry
from src.modules.ai_assistant.application.tools.schemas import build_ollama_tools_payload

_FENCED_JSON_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)

# 1 tool call + 1 follow-up covers everything observed empirically; bounded
# well above that as a hard safety cap against a model that keeps
# requesting tools instead of ever answering.
_MAX_TOOL_ITERATIONS = 4

_SYSTEM_PROMPT_TOOLS_SUFFIX = (
    "\n\nTu as accès à des outils pour consulter des données réelles ou "
    "effectuer certaines actions. Utilise un outil UNIQUEMENT si la "
    "question porte sur des données précises que tu ne connais pas ou "
    "nécessite une action. Pour toute autre question (salutations, "
    "remarques générales, questions déjà répondues dans la conversation), "
    "réponds normalement en français, en texte libre, SANS JSON — ignore "
    "la liste d'outils dans ce cas."
)


_FALLBACK_REPLY = (
    "J'ai bien consulté les informations demandées, mais je n'ai pas réussi "
    "à formuler une réponse claire à partir de ce résultat — n'hésite pas à "
    "reformuler ta question."
)


@dataclass(frozen=True)
class ToolLoopResult:
    reply: str
    tools_invoked: list[str] = field(default_factory=list)


def _looks_like_unparsed_json(content: str) -> bool:
    """Catches JSON the model produced that ISN'T a `{"name", "arguments"}`
    tool call (so `OllamaClient`'s own parsing lets it through as
    `tool_call=None`) but is still not a natural-language answer — e.g. a
    hallucinated data object like `{"alert_id": ..., "symbol": ...}`,
    empirically observed once the conversation already has several rounds
    of JSON tool-call/tool-result messages in it. Any top-level JSON
    object/array must never be shown to the user as a "reply"."""
    text = content.strip()
    fenced = _FENCED_JSON_RE.match(text)
    if fenced:
        text = fenced.group(1).strip()
    if not text or text[0] not in "{[":
        return False
    try:
        json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return False
    return True


def _safe_reply(result) -> str:
    """A no-tools call is only a valid final answer if the model actually
    produced free text — with several rounds of JSON tool-call/tool-result
    messages already in its context, a small model can keep emitting
    JSON-shaped content even once `tools` is empty. Raw JSON must never
    reach the user (empirically observed: the model looped on `list_alerts`
    for every iteration and its "final" no-tools call was still JSON, and
    separately hallucinated a JSON data object unrelated to any tool)."""
    if result.tool_call is not None or _looks_like_unparsed_json(result.content):
        return _FALLBACK_REPLY
    return result.content


class ToolCallingLoop:
    def __init__(self, ollama_chat_with_tools, tool_registry: ToolRegistry) -> None:
        self._ollama_chat_with_tools = ollama_chat_with_tools
        self._tool_registry = tool_registry

    async def run(
        self,
        messages: list[dict],
        user_id: int,
        tools_enabled: bool,
        temperature: float,
        max_tokens: int,
    ) -> ToolLoopResult:
        if not tools_enabled:
            result = self._ollama_chat_with_tools(messages, [], temperature, max_tokens)
            return ToolLoopResult(reply=_safe_reply(result), tools_invoked=[])

        messages = list(messages)
        messages[0] = {
            **messages[0],
            "content": messages[0]["content"] + _SYSTEM_PROMPT_TOOLS_SUFFIX,
        }
        tools_payload = build_ollama_tools_payload()
        invoked: list[str] = []

        for _ in range(_MAX_TOOL_ITERATIONS):
            result = self._ollama_chat_with_tools(messages, tools_payload, temperature, max_tokens)
            if result.tool_call is None:
                return ToolLoopResult(reply=_safe_reply(result), tools_invoked=invoked)

            name = result.tool_call["name"]
            arguments = result.tool_call.get("arguments", {})
            if name not in self._tool_registry.dispatch:
                # Hallucinated/unknown tool name: never show raw JSON to the
                # user, retry once forcing a plain-language answer instead.
                plain = self._ollama_chat_with_tools(messages, [], temperature, max_tokens)
                return ToolLoopResult(reply=_safe_reply(plain), tools_invoked=invoked)

            messages.append({"role": "assistant", "content": json.dumps(result.tool_call)})
            tool_result = await self._tool_registry.dispatch[name](arguments, user_id)
            invoked.append(name)
            messages.append(
                {"role": "tool", "name": name, "content": json.dumps(tool_result)}
            )

        # Loop exhausted without a plain-text answer: force one final
        # no-tools call so the user still gets a natural-language reply.
        final = self._ollama_chat_with_tools(messages, [], temperature, max_tokens)
        return ToolLoopResult(reply=_safe_reply(final), tools_invoked=invoked)

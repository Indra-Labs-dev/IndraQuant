from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from src.modules.ai_assistant.application.tool_calling_loop import ToolCallingLoop
from src.modules.ai_assistant.domain.repositories import (
    ChatRepository,
    ConversationRepository,
    MemoryRepository,
)
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
_DEFAULT_TOOLS_ENABLED = True

# Conversation titles are derived from the first message rather than a
# dedicated LLM call — simple, free, and matches what ChatGPT shows in its
# sidebar before a conversation has been summarized.
_TITLE_MAX_LENGTH = 120


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None


class ChatResponse(BaseModel):
    reply: str
    model: str
    context_note: str
    tools_invoked: list[str] = Field(default_factory=list)
    conversation_id: int


_SYSTEM_PROMPT = (
    "SYSTEM PROMPT — INDRAQUANT AI\n\n"
    "TU ES L'ASSISTANT OFFICIEL D'INDRAQUANT, UNE PLATEFORME PERSONNELLE D'AIDE À LA DÉCISION POUR LES MARCHÉS FINANCIERS.\n\n"
    "Ta mission est d'aider l'utilisateur à comprendre les marchés, interpréter les données disponibles, identifier les scénarios possibles et améliorer sa prise de décision.\n\n"
    "Tu n'es PAS un conseiller financier et tu ne prends jamais de décision à la place de l'utilisateur.\n\n"
    "──────────────────────────────────\n"
    "OBJECTIFS\n"
    "──────────────────────────────────\n\n"
    "Tu dois systématiquement :\n\n"
    "• expliquer les phénomènes de marché de manière claire ;\n"
    "• transformer des données complexes en informations exploitables ;\n"
    "• distinguer les faits des hypothèses ;\n"
    "• mettre en évidence les risques ;\n"
    "• présenter plusieurs scénarios lorsque l'avenir est incertain ;\n"
    "• aider l'utilisateur à construire son propre raisonnement.\n\n"
    "Tu privilégies la qualité du raisonnement plutôt que la quantité de texte.\n\n"
    "Tu réponds toujours en français, sauf demande explicite contraire.\n\n"
    "──────────────────────────────────\n"
    "STYLE\n"
    "──────────────────────────────────\n\n"
    "Ton style est :\n\n"
    "- précis\n"
    "- professionnel\n"
    "- neutre\n"
    "- pédagogique\n"
    "- synthétique\n"
    "- sans sensationnalisme\n"
    "- sans jargon inutile\n\n"
    "Tu évites :\n\n"
    "- les phrases vagues\n"
    "- les affirmations excessives\n"
    "- les réponses marketing\n"
    "- les tournures émotionnelles\n\n"
    "──────────────────────────────────\n"
    "RÈGLES ABSOLUES\n"
    "──────────────────────────────────\n\n"
    "NE JAMAIS :\n\n"
    "• prédire avec certitude l'évolution future d'un actif.\n\n"
    "• utiliser des formulations comme :\n\n"
    "\"Le prix va monter.\"\n\n"
    "\"Cette action va exploser.\"\n\n"
    "\"Achète maintenant.\"\n\n"
    "\"Cette crypto est garantie.\"\n\n"
    "Préférer :\n\n"
    "\"Le contexte actuel augmente la probabilité de...\"\n\n"
    "\"Le scénario dominant semble être...\"\n\n"
    "\"Sous réserve que...\"\n\n"
    "\"Les données disponibles suggèrent...\"\n\n"
    "Toujours rappeler implicitement ou explicitement que :\n\n"
    "- les marchés restent imprévisibles ;\n"
    "- toute analyse comporte une part d'incertitude ;\n"
    "- les probabilités peuvent évoluer rapidement.\n\n"
    "Ne jamais présenter une opinion comme un fait.\n\n"
    "──────────────────────────────────\n"
    "NON-CONSEIL EN INVESTISSEMENT\n"
    "──────────────────────────────────\n\n"
    "Lorsque la discussion porte sur un investissement, une stratégie, un achat ou une vente, rappeler que :\n\n"
    "\"Cette analyse constitue une aide à la décision et ne constitue pas un conseil en investissement.\"\n\n"
    "Ne pas répéter cette phrase inutilement si elle a déjà été mentionnée récemment dans la conversation.\n\n"
    "──────────────────────────────────\n"
    "HIÉRARCHIE DES SOURCES\n"
    "──────────────────────────────────\n\n"
    "Lorsque plusieurs informations sont disponibles, les prioriser dans cet ordre :\n\n"
    "1. contexte de marché fourni\n"
    "2. mémoire utilisateur\n"
    "3. message utilisateur\n"
    "4. connaissances générales\n\n"
    "Ne jamais inventer une donnée absente.\n\n"
    "En cas de conflit entre plusieurs informations, signaler explicitement l'incohérence.\n\n"
    "──────────────────────────────────\n"
    "UTILISATION DU CONTEXTE\n"
    "──────────────────────────────────\n\n"
    "Contexte actuel :\n\n"
    "{context}\n\n"
    "Utilise ce contexte uniquement lorsqu'il est pertinent.\n\n"
    "Ne répète pas inutilement les informations déjà présentes.\n\n"
    "S'il manque des données importantes pour répondre correctement, indique clairement quelles informations font défaut.\n\n"
    "──────────────────────────────────\n"
    "UTILISATION DE LA MÉMOIRE\n"
    "──────────────────────────────────\n\n"
    "Mémoire utilisateur :\n\n"
    "{memory}\n\n"
    "Considère cette mémoire comme une liste de préférences et de faits historiques.\n\n"
    "Ne la traite jamais comme une vérité absolue.\n\n"
    "Si une information récente contredit la mémoire, privilégie l'information la plus récente.\n\n"
    "──────────────────────────────────\n"
    "MÉTHODE DE RAISONNEMENT\n"
    "──────────────────────────────────\n\n"
    "Avant de répondre, applique mentalement les étapes suivantes :\n\n"
    "1. Identifier la véritable question.\n\n"
    "2. Déterminer si le contexte actuel contient des informations utiles.\n\n"
    "3. Séparer :\n\n"
    "- faits\n"
    "- hypothèses\n"
    "- opinions\n"
    "- incertitudes\n\n"
    "4. Identifier :\n\n"
    "- opportunités\n"
    "- risques\n"
    "- éléments manquants\n\n"
    "5. Construire une réponse logique.\n\n"
    "6. Vérifier qu'aucune affirmation n'est présentée comme certaine si elle concerne le futur.\n\n"
    "Ne révèle jamais ce raisonnement interne.\n\n"
    "──────────────────────────────────\n"
    "GESTION DE L'INCERTITUDE\n"
    "──────────────────────────────────\n\n"
    "Lorsque les données sont ambiguës :\n\n"
    "- présenter plusieurs scénarios ;\n"
    "- expliquer ce qui invaliderait chaque scénario ;\n"
    "- indiquer le niveau de confiance.\n\n"
    "Utiliser une échelle telle que :\n\n"
    "Confiance :\n"
    "Très faible\n"
    "Faible\n"
    "Modérée\n"
    "Élevée\n\n"
    "Cette confiance reflète uniquement la qualité des informations disponibles.\n\n"
    "──────────────────────────────────\n"
    "ANALYSE FINANCIÈRE\n"
    "──────────────────────────────────\n\n"
    "Lorsque tu analyses un actif, considérer si pertinent :\n\n"
    "• tendance\n"
    "• volatilité\n"
    "• momentum\n"
    "• supports\n"
    "• résistances\n"
    "• volume\n"
    "• liquidité\n"
    "• contexte macro\n"
    "• politique monétaire\n"
    "• résultats financiers\n"
    "• valorisation\n"
    "• risque\n"
    "• sentiment de marché\n\n"
    "Ne pas forcer l'analyse si les données sont absentes.\n\n"
    "──────────────────────────────────\n"
    "FORMAT DE RÉPONSE\n"
    "──────────────────────────────────\n\n"
    "Lorsque pertinent, organiser la réponse selon cette structure :\n\n"
    "### Synthèse\n\n"
    "Réponse courte.\n\n"
    "### Analyse\n\n"
    "Explication détaillée.\n\n"
    "### Points favorables\n\n"
    "- ...\n\n"
    "### Risques\n\n"
    "- ...\n\n"
    "### Scénarios possibles\n\n"
    "Scénario principal\n\n"
    "Scénario alternatif\n\n"
    "Scénario défavorable\n\n"
    "### Niveau de confiance\n\n"
    "Faible / Modéré / Élevé\n\n"
    "### Conclusion\n\n"
    "Résumer en quelques phrases.\n\n"
    "Si la question est simple, répondre simplement sans forcer cette structure.\n\n"
    "──────────────────────────────────\n"
    "GESTION DES HALLUCINATIONS\n"
    "──────────────────────────────────\n\n"
    "Ne jamais :\n\n"
    "- inventer un prix ;\n"
    "- inventer une statistique ;\n"
    "- inventer une actualité ;\n"
    "- inventer un indicateur ;\n"
    "- inventer une source.\n\n"
    "Lorsque tu ne sais pas :\n\n"
    "Dire clairement :\n\n"
    "\"Je ne dispose pas de cette information.\"\n\n"
    "ou\n\n"
    "\"Les données fournies ne permettent pas de conclure.\"\n\n"
    "──────────────────────────────────\n"
    "OBJECTIF FINAL\n"
    "──────────────────────────────────\n\n"
    "Ton objectif est d'augmenter la qualité des décisions de l'utilisateur en fournissant une analyse rigoureuse, nuancée, transparente et fondée sur les informations disponibles, sans jamais transformer une probabilité en certitude ni une analyse en recommandation d'investissement."
)


class ChatUseCase:
    def __init__(
        self,
        instruments: ListInstrumentsUseCase,
        ohlcv: OhlcvProvider,
        tool_calling_loop: ToolCallingLoop,
        chat_repository: ChatRepository,
        memory_repository: MemoryRepository,
        extract_memory_facts,
        settings_repository: SettingsRepository,
        conversation_repository: ConversationRepository,
    ) -> None:
        self._instruments = instruments
        self._ohlcv = ohlcv
        self._tool_calling_loop = tool_calling_loop
        self._chat_repository = chat_repository
        self._memory_repository = memory_repository
        self._extract_memory_facts = extract_memory_facts
        self._settings_repository = settings_repository
        self._conversation_repository = conversation_repository

    async def execute(self, user_id: int, request: ChatRequest) -> ChatResponse:
        if request.conversation_id is None:
            conversation = await self._conversation_repository.create_conversation(
                user_id, title=request.message[:_TITLE_MAX_LENGTH]
            )
            conversation_id = conversation.id
        else:
            conversation_id = request.conversation_id

        context = await self._market_context()
        known_facts = [f.content for f in await self._memory_repository.list_facts(user_id)]
        memory_block = "\n".join(f"- {f}" for f in known_facts) or "(aucun pour l'instant)"
        history = await self._chat_repository.list_recent(
            user_id, conversation_id, _HISTORY_LIMIT
        )
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
        temperature, max_tokens, tools_enabled = await self._chat_parameters(user_id)
        try:
            loop_result = await self._tool_calling_loop.run(
                messages, user_id, tools_enabled, temperature, max_tokens
            )
        except Exception as error:
            raise AppError(
                "assistant_unavailable",
                f"Assistant indisponible (Ollama) : {error}",
                http_status=502,
            )
        reply = loop_result.reply

        await self._chat_repository.add_message(
            user_id, conversation_id, "user", request.message
        )
        await self._chat_repository.add_message(
            user_id, conversation_id, "assistant", reply
        )

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
            tools_invoked=loop_result.tools_invoked,
            conversation_id=conversation_id,
        )

    async def _chat_parameters(self, user_id: int) -> tuple[float, int, bool]:
        settings = {s.key: s.value for s in await self._settings_repository.get_all(user_id)}
        temperature = _DEFAULT_TEMPERATURE
        max_tokens = _DEFAULT_MAX_TOKENS
        tools_enabled = _DEFAULT_TOOLS_ENABLED
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
        if "ai_tools_enabled" in settings:
            tools_enabled = settings["ai_tools_enabled"].strip().lower() not in ("false", "0", "")
        return temperature, max_tokens, tools_enabled

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

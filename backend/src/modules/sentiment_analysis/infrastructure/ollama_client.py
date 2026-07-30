import json
import os
from concurrent.futures import ThreadPoolExecutor

import httpx

# Ollama tourne nativement sur l'hote (acces GPU) meme quand le backend est
# conteneurise - OLLAMA_BASE_URL permet de le joindre via host.docker.internal
# dans ce cas (voir docker-compose.yml), 127.0.0.1 restant le defaut pour une
# execution native du backend.
_OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
_OLLAMA_URL = f"{_OLLAMA_BASE_URL}/api/generate"
_OLLAMA_CHAT_URL = f"{_OLLAMA_BASE_URL}/api/chat"
_MODEL = "qwen2.5-coder:3b"
_TIMEOUT_SECONDS = 60
_CHAT_TIMEOUT_SECONDS = 120
# One classification call per headline is unavoidable (Ollama's JSON mode only
# reliably yields a single object per request), but nothing requires firing
# them one after another: Ollama accepts concurrent requests (serialized or
# parallelized server-side depending on its own OLLAMA_NUM_PARALLEL setting),
# so issuing them concurrently can only help, never hurt, wall-clock latency
# (docs/roadmap #17 — parallélisation). Bounded to avoid overwhelming a
# single local Ollama instance with dozens of simultaneous requests.
_MAX_CONCURRENT_CLASSIFICATIONS = 4


class OllamaClient:
    def chat(self, messages: list[dict]) -> str:
        response = httpx.post(
            _OLLAMA_CHAT_URL,
            json={
                "model": _MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.3},
            },
            timeout=_CHAT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "")

    def classify_headlines(self, headlines: list[str]) -> list[dict]:
        """One {"sentiment", "score", "rationale"} per headline. The JSON
        mode of Ollama reliably yields a single object per request, so each
        headline is classified in its own call (results are cached upstream) —
        fired concurrently rather than sequentially (docs/roadmap #17)."""
        if not headlines:
            return []
        with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
            with ThreadPoolExecutor(
                max_workers=min(_MAX_CONCURRENT_CLASSIFICATIONS, len(headlines))
            ) as executor:
                return list(
                    executor.map(lambda h: self._classify_one(client, h), headlines)
                )

    def _classify_one(self, client: httpx.Client, headline: str) -> dict:
        prompt = (
            "Tu es un analyste financier. Donne le sentiment de marché de ce "
            "titre d'actualité. Réponds UNIQUEMENT un objet JSON de la forme "
            '{"sentiment": "positif|negatif|neutre", "score": nombre entre '
            '-1.0 et 1.0, "rationale": "justification courte en français"}.\n'
            f"Titre : {headline}"
        )
        try:
            response = client.post(
                _OLLAMA_URL,
                json={
                    "model": _MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1},
                },
            )
            response.raise_for_status()
            parsed = json.loads(response.json().get("response", "{}"))
            sentiment = str(parsed.get("sentiment", "neutre")).lower()
            if sentiment not in ("positif", "negatif", "neutre"):
                sentiment = "neutre"
            return {
                "sentiment": sentiment,
                "score": float(parsed.get("score", 0.0)),
                "rationale": str(parsed.get("rationale", "")),
            }
        except (httpx.HTTPError, json.JSONDecodeError, TypeError, ValueError):
            return {
                "sentiment": "neutre",
                "score": 0.0,
                "rationale": "Classification indisponible pour ce titre.",
            }

    _CATEGORIES = (
        "réglementation", "macroéconomie", "technologie/produit",
        "sécurité/piratage", "partenariat/adoption", "marché/prix", "autre",
    )
    _IMPACTS = ("faible", "moyen", "élevé")

    def classify_news_intelligence(self, headlines: list[str]) -> list[dict]:
        """One {"category", "is_event", "event_type", "impact"} per
        headline (docs/roadmap #14: classification automatique, détection
        d'événements, estimation d'impact) — a single extended JSON-mode
        call per headline, fired concurrently (docs/roadmap #17), same
        pattern as `classify_headlines`."""
        if not headlines:
            return []
        with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
            with ThreadPoolExecutor(
                max_workers=min(_MAX_CONCURRENT_CLASSIFICATIONS, len(headlines))
            ) as executor:
                return list(
                    executor.map(
                        lambda h: self._classify_news_intelligence_one(client, h), headlines
                    )
                )

    def _classify_news_intelligence_one(self, client: httpx.Client, headline: str) -> dict:
        categories = ", ".join(self._CATEGORIES)
        prompt = (
            "Tu es un analyste financier. Analyse ce titre d'actualité et "
            "réponds UNIQUEMENT un objet JSON de la forme "
            f'{{"category": une valeur parmi [{categories}], '
            '"is_event": true si le titre décrit un événement précis et daté '
            "(décision réglementaire, piratage, annonce de produit, résultat "
            "financier...) plutôt qu'un commentaire général, false sinon, "
            '"event_type": description courte en français de l\'événement '
            'si is_event est vrai sinon chaîne vide, '
            f'"impact": une valeur parmi [{", ".join(self._IMPACTS)}] estimant '
            "l'impact probable sur le marché}.\n"
            f"Titre : {headline}"
        )
        try:
            response = client.post(
                _OLLAMA_URL,
                json={
                    "model": _MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1},
                },
            )
            response.raise_for_status()
            parsed = json.loads(response.json().get("response", "{}"))
            category = str(parsed.get("category", "autre")).lower()
            if category not in self._CATEGORIES:
                category = "autre"
            impact = str(parsed.get("impact", "faible")).lower()
            if impact not in self._IMPACTS:
                impact = "faible"
            return {
                "category": category,
                "is_event": bool(parsed.get("is_event", False)),
                "event_type": str(parsed.get("event_type", "")),
                "impact": impact,
            }
        except (httpx.HTTPError, json.JSONDecodeError, TypeError, ValueError):
            return {
                "category": "autre",
                "is_event": False,
                "event_type": "",
                "impact": "faible",
            }

    def summarize_cluster(self, titles: list[str]) -> str:
        """One short French summary for a cluster of headlines describing
        the same underlying story across multiple sources (docs/roadmap
        #14: résumé multi-sources)."""
        if len(titles) == 1:
            return titles[0]
        bullet_list = "\n".join(f"- {t}" for t in titles)
        prompt = (
            "Ces titres décrivent probablement la même actualité, rapportée "
            "par plusieurs sources. Résume-la en une phrase factuelle en "
            "français, sans opinion. Réponds uniquement la phrase, sans "
            f"guillemets.\n{bullet_list}"
        )
        try:
            response = httpx.post(
                _OLLAMA_URL,
                json={
                    "model": _MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
                timeout=_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            summary = response.json().get("response", "").strip()
            return summary or titles[0]
        except (httpx.HTTPError, TypeError, ValueError):
            return titles[0]

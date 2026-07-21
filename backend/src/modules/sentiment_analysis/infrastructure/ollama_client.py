import json

import httpx

_OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
_OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
_MODEL = "llama3.1:8b"
_TIMEOUT_SECONDS = 60
_CHAT_TIMEOUT_SECONDS = 120


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
        headline is classified in its own call (results are cached upstream).
        """
        results: list[dict] = []
        with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
            for headline in headlines:
                results.append(self._classify_one(client, headline))
        return results

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

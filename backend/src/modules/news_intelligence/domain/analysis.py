"""News Intelligence (docs/roadmap #14): pure functions for multi-source
clustering, source credibility, and news/price correlation. LLM-backed
classification (category/event/impact) and cluster summaries live in
`sentiment_analysis.infrastructure.ollama_client` — this file only
contains logic that needs no external call.
"""

import math
import re
from dataclasses import dataclass

# Static credibility registry for the RSS sources currently wired
# (ADR-018) — a simple, explicit, extensible stand-in for a real
# editorial-reputation scoring service. New sources default to "moyenne"
# rather than silently being trusted or distrusted.
_SOURCE_CREDIBILITY: dict[str, float] = {
    "CoinDesk": 0.85,
    "Cointelegraph": 0.65,
    "Yahoo Finance": 0.9,
}
_DEFAULT_CREDIBILITY = 0.5

_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is",
    "are", "with", "at", "by", "from", "as", "it", "its", "this", "that",
    "le", "la", "les", "de", "des", "du", "un", "une", "et", "en", "au",
    "aux", "pour", "sur", "avec", "dans", "ce", "cette", "ces", "son", "sa",
}


@dataclass(frozen=True)
class CredibilityResult:
    source: str
    score: float
    level: str  # "faible" | "moyenne" | "élevée"
    explanation: str


def credibility_score(source: str) -> CredibilityResult:
    score = _SOURCE_CREDIBILITY.get(source, _DEFAULT_CREDIBILITY)
    level = "élevée" if score >= 0.75 else "moyenne" if score >= 0.5 else "faible"
    known = source in _SOURCE_CREDIBILITY
    return CredibilityResult(
        source,
        score,
        level,
        f"Crédibilité {level} ({score * 100:.0f}/100)"
        + ("." if known else " — source non répertoriée, score par défaut."),
    )


def significant_tokens(title: str) -> set[str]:
    words = re.findall(r"[a-zA-ZÀ-ÿ0-9']+", title.lower())
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def cluster_headlines(titles: list[str], min_similarity: float = 0.3) -> list[list[int]]:
    """Groups headline *indices* that likely describe the same underlying
    story (multi-source deduplication) using Jaccard similarity of their
    significant words — a greedy, deterministic, LLM-free clustering."""
    token_sets = [significant_tokens(t) for t in titles]
    assigned = [False] * len(titles)
    clusters: list[list[int]] = []

    for i in range(len(titles)):
        if assigned[i]:
            continue
        cluster = [i]
        assigned[i] = True
        for j in range(i + 1, len(titles)):
            if assigned[j]:
                continue
            if jaccard_similarity(token_sets[i], token_sets[j]) >= min_similarity:
                cluster.append(j)
                assigned[j] = True
        clusters.append(cluster)
    return clusters


def news_price_correlation(
    daily_sentiment: list[float], daily_returns: list[float]
) -> float | None:
    """Same-day (contemporaneous) Pearson correlation between average news
    sentiment and the instrument's price return — describes whether
    sentiment and price *moved together* historically, not whether
    sentiment predicts future price."""
    n = len(daily_sentiment)
    if n < 5 or n != len(daily_returns):
        return None
    mean_s = sum(daily_sentiment) / n
    mean_r = sum(daily_returns) / n
    cov = sum((s - mean_s) * (r - mean_r) for s, r in zip(daily_sentiment, daily_returns))
    var_s = sum((s - mean_s) ** 2 for s in daily_sentiment)
    var_r = sum((r - mean_r) ** 2 for r in daily_returns)
    denom = math.sqrt(var_s * var_r)
    return cov / denom if denom > 0 else None

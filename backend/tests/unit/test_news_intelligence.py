from src.modules.news_intelligence.domain.analysis import (
    cluster_headlines,
    credibility_score,
    jaccard_similarity,
    news_price_correlation,
    significant_tokens,
)


def test_credibility_score_known_source():
    result = credibility_score("Yahoo Finance")
    assert result.level == "élevée"
    assert result.score > 0.75


def test_credibility_score_unknown_source_defaults_moderate():
    result = credibility_score("Some Random Blog")
    assert result.level == "moyenne"
    assert "non répertoriée" in result.explanation


def test_significant_tokens_strips_stopwords_and_short_words():
    tokens = significant_tokens("The Bitcoin ETF is a big deal for the market")
    assert "the" not in tokens
    assert "is" not in tokens
    assert "bitcoin" in tokens
    assert "market" in tokens


def test_jaccard_similarity_identical_sets():
    a = {"bitcoin", "etf", "approval"}
    assert jaccard_similarity(a, a) == 1.0


def test_jaccard_similarity_disjoint_sets():
    assert jaccard_similarity({"bitcoin"}, {"ethereum"}) == 0.0


def test_jaccard_similarity_empty_sets():
    assert jaccard_similarity(set(), {"bitcoin"}) == 0.0


def test_cluster_headlines_groups_similar_titles():
    titles = [
        "Bitcoin ETF approval sends prices higher",
        "Bitcoin ETF approved, prices surge higher",
        "Ethereum developers announce new upgrade",
    ]
    clusters = cluster_headlines(titles, min_similarity=0.3)
    assert len(clusters) == 2
    sizes = sorted(len(c) for c in clusters)
    assert sizes == [1, 2]


def test_cluster_headlines_all_distinct():
    titles = ["Completely unrelated story one", "Totally different story two"]
    clusters = cluster_headlines(titles, min_similarity=0.5)
    assert len(clusters) == 2


def test_news_price_correlation_none_with_insufficient_history():
    assert news_price_correlation([0.1, 0.2], [0.01, 0.02]) is None


def test_news_price_correlation_positive_when_aligned():
    sentiment = [0.5, 0.4, -0.3, -0.5, 0.6, 0.3]
    returns = [0.02, 0.015, -0.01, -0.02, 0.025, 0.01]
    correlation = news_price_correlation(sentiment, returns)
    assert correlation is not None
    assert correlation > 0.5


def test_news_price_correlation_none_with_zero_variance():
    assert news_price_correlation([0.1] * 10, [0.01, 0.02, 0.03, 0.01, 0.02, 0.01, 0.02, 0.03, 0.01, 0.02]) is None

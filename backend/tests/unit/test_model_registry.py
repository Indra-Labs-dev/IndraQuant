from src.modules.model_registry.domain.registry import compare_model_types, decide_champion


def test_decide_champion_first_version_always_promoted():
    decision = decide_champion(0.55, 0.50, None)
    assert decision.promoted is True
    assert decision.model_type == "xgboost"


def test_decide_champion_picks_higher_accuracy_model_type():
    decision = decide_champion(0.48, 0.60, None)
    assert decision.model_type == "logistic_regression"


def test_decide_champion_promotes_when_better_than_prior_champion():
    decision = decide_champion(0.62, 0.55, 0.58)
    assert decision.promoted is True


def test_decide_champion_stays_challenger_when_worse():
    decision = decide_champion(0.50, 0.52, 0.60)
    assert decision.promoted is False


def test_decide_champion_ties_promote():
    decision = decide_champion(0.55, 0.50, 0.55)
    assert decision.promoted is True


def test_compare_model_types_picks_higher_mean_edge():
    xgboost_edges = [0.05, 0.06, 0.04, 0.07, 0.05, 0.06, 0.05, 0.04, 0.06, 0.05,
                      0.05, 0.06, 0.04, 0.07, 0.05, 0.06, 0.05, 0.04, 0.06, 0.05]
    logreg_edges = [0.01, 0.0, 0.02, -0.01, 0.01, 0.0, 0.01, 0.02, 0.0, 0.01,
                    0.01, 0.0, 0.02, -0.01, 0.01, 0.0, 0.01, 0.02, 0.0, 0.01]
    result = compare_model_types(xgboost_edges, logreg_edges)
    assert result.winner == "xgboost"
    assert result.xgboost_edge[0] > result.logistic_regression_edge[0]


def test_compare_model_types_insufficient_data_returns_zero_ci():
    result = compare_model_types([0.05, 0.06], [0.01, 0.02])
    assert result.xgboost_edge == (0.0, 0.0, 0.0)

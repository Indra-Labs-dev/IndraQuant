import json

from src.modules.explainable_ai.domain.analysis import FeatureContributionPoint


def parse_contributions(shap_json: str | None) -> list[FeatureContributionPoint]:
    """Deserializes the `shap_json` column persisted by `PredictDirectionUseCase`
    (migration 006) back into domain value objects. Predictions made before
    this feature shipped have `shap_json = NULL` and yield an empty list."""
    if not shap_json:
        return []
    try:
        raw = json.loads(shap_json)
    except (TypeError, ValueError):
        return []
    return [
        FeatureContributionPoint(
            feature=item["feature"], value=item["value"], contribution=item["contribution"]
        )
        for item in raw
    ]

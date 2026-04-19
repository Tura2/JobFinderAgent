import json
import logging
from app.models.cv_variant import CVVariant

logger = logging.getLogger(__name__)


def _extract_keywords(name: str) -> set[str]:
    return {w.lower().strip() for w in name.replace("-", " ").replace("_", " ").split() if w.strip()}


def select_cv_variant(
    recommended_name: str,
    active_variants: list[CVVariant],
) -> list[CVVariant]:
    if not active_variants:
        return []

    for v in active_variants:
        if v.name.lower() == recommended_name.lower():
            return [v]

    keywords = _extract_keywords(recommended_name)

    scored: list[tuple[int, CVVariant]] = []
    for v in active_variants:
        try:
            tags = set(json.loads(v.focus_tags))
        except (json.JSONDecodeError, TypeError):
            tags = set()
        overlap = len(keywords & {t.lower() for t in tags})
        scored.append((overlap, v))

    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        return []

    best_score = scored[0][0]

    if best_score == 0:
        return [active_variants[0]]

    tied = [v for score, v in scored if score == best_score]
    if len(tied) >= 2:
        return tied[:2]

    return [scored[0][1]]

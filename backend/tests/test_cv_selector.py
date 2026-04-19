import pytest
import json
from sqlmodel import Session

from app.models.cv_variant import CVVariant
from app.pipeline.cv_selector import select_cv_variant


def _seed_variants(db: Session) -> list[CVVariant]:
    variants = [
        CVVariant(
            name="frontend-focused",
            file_path="/cv/frontend.pdf",
            focus_tags=json.dumps(["react", "ui", "design-systems", "css"]),
            is_active=True,
        ),
        CVVariant(
            name="fullstack-automation",
            file_path="/cv/fullstack.pdf",
            focus_tags=json.dumps(["node", "deploy", "electron", "automation"]),
            is_active=True,
        ),
        CVVariant(
            name="ai-builder",
            file_path="/cv/ai.pdf",
            focus_tags=json.dumps(["llm", "openai", "langchain", "automation"]),
            is_active=True,
        ),
    ]
    for v in variants:
        db.add(v)
    db.commit()
    for v in variants:
        db.refresh(v)
    return variants


def test_select_by_exact_name(db: Session):
    variants = _seed_variants(db)
    result = select_cv_variant("frontend-focused", variants)
    assert len(result) == 1
    assert result[0].name == "frontend-focused"


def test_select_by_name_case_insensitive(db: Session):
    variants = _seed_variants(db)
    result = select_cv_variant("Frontend-Focused", variants)
    assert len(result) == 1
    assert result[0].name == "frontend-focused"


def test_fallback_to_tag_matching(db: Session):
    variants = _seed_variants(db)
    result = select_cv_variant("react-specialist", variants)
    assert len(result) >= 1
    assert any(v.name == "frontend-focused" for v in result)


def test_ambiguous_returns_multiple(db: Session):
    variants = _seed_variants(db)
    result = select_cv_variant("automation-expert", variants)
    assert len(result) == 2
    names = {v.name for v in result}
    assert "fullstack-automation" in names
    assert "ai-builder" in names


def test_no_match_returns_first_active(db: Session):
    variants = _seed_variants(db)
    result = select_cv_variant("completely-unrelated-xyz", variants)
    assert len(result) == 1


def test_empty_variants_returns_empty(db: Session):
    result = select_cv_variant("anything", [])
    assert result == []

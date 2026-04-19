"""LLM-as-judge evaluator for agent output quality.

Scores each agent's output on a 4-point rubric:
  schema_validity, factual_grounding, constraint_adherence, no_hallucination

Runs against a fixed test set. Fails if mean score < 0.8.
"""
from __future__ import annotations

import json
import sys
from typing import Any

import pytest
from pydantic import BaseModel

TEST_CASES: list[dict[str, Any]] = [
    {
        "input": "LKR 3000 for two people, spicy Sri Lankan, no seafood",
        "agent": "planner",
        "expected_fields": {
            "budget_lkr": 3000.0,
            "party_size": 2,
            "cuisines": ["sri_lankan"],
            "dietary_exclude_contains": ["seafood"],
            "spice_preference": "hot",
        },
    },
    {
        "input": "Budget 2500 rupees, want vegetarian Indian for one person",
        "agent": "planner",
        "expected_fields": {
            "budget_lkr": 2500.0,
            "party_size": 1,
            "cuisines": ["indian"],
            "dietary_require_contains": ["vegetarian"],
        },
    },
    {
        "input": "Rs 4000 for Italian food, 3 people, no pork",
        "agent": "planner",
        "expected_fields": {
            "budget_lkr": 4000.0,
            "party_size": 3,
            "cuisines": ["italian"],
            "dietary_exclude_contains": ["pork"],
        },
    },
    {
        "input": "spend 1800 rupees on Chinese food",
        "agent": "planner",
        "expected_fields": {
            "budget_lkr": 1800.0,
            "cuisines": ["chinese"],
        },
    },
    {
        "input": "LKR 5000 Japanese food for two, no pork",
        "agent": "planner",
        "expected_fields": {
            "budget_lkr": 5000.0,
            "party_size": 2,
            "cuisines": ["japanese"],
            "dietary_exclude_contains": ["pork"],
        },
    },
]


def score_planner_output(parsed: Any, expected: dict) -> dict[str, float]:
    """Score a planner output against expected fields. Returns per-dimension scores 0–1."""
    scores: dict[str, float] = {}

    # schema_validity: did we get a valid ParsedRequest-like object?
    try:
        assert hasattr(parsed, "budget_lkr")
        assert hasattr(parsed, "party_size")
        assert hasattr(parsed, "cuisines")
        scores["schema_validity"] = 1.0
    except AssertionError:
        scores["schema_validity"] = 0.0

    # factual_grounding: numeric fields match expected values
    fg = 0.0
    checks = 0
    if "budget_lkr" in expected:
        checks += 1
        fg += 1.0 if abs(parsed.budget_lkr - expected["budget_lkr"]) < 0.01 else 0.0
    if "party_size" in expected:
        checks += 1
        fg += 1.0 if parsed.party_size == expected["party_size"] else 0.0
    scores["factual_grounding"] = fg / checks if checks > 0 else 1.0

    # constraint_adherence: cuisines, dietary fields
    ca = 0.0
    checks = 0
    if "cuisines" in expected:
        checks += 1
        ca += 1.0 if set(expected["cuisines"]).issubset(set(parsed.cuisines)) else 0.0
    if "dietary_exclude_contains" in expected:
        checks += 1
        ca += 1.0 if set(expected["dietary_exclude_contains"]).issubset(set(parsed.dietary_exclude)) else 0.0
    if "dietary_require_contains" in expected:
        checks += 1
        ca += 1.0 if set(expected["dietary_require_contains"]).issubset(set(parsed.dietary_require)) else 0.0
    if "spice_preference" in expected:
        checks += 1
        ca += 1.0 if parsed.spice_preference == expected["spice_preference"] else 0.0
    scores["constraint_adherence"] = ca / checks if checks > 0 else 1.0

    # no_hallucination: no fields invented that user didn't mention
    # (basic check: dietary_exclude and dietary_require should not grow beyond expected)
    nh = 1.0
    if "dietary_exclude_contains" not in expected and parsed.dietary_exclude:
        nh -= 0.3
    if "dietary_require_contains" not in expected and parsed.dietary_require:
        nh -= 0.3
    if "spice_preference" not in expected and parsed.spice_preference is not None:
        nh -= 0.2
    scores["no_hallucination"] = max(0.0, nh)

    return scores


def run_judge() -> dict[str, Any]:
    from src.agents.planner import run_planner
    from src.state import GraphState

    all_scores: list[float] = []
    results = []

    for case in TEST_CASES:
        state = GraphState(trace_id="judge-eval", user_input=case["input"])
        result = run_planner(state)
        parsed = result.get("parsed")

        if parsed is None:
            case_scores = {k: 0.0 for k in ["schema_validity", "factual_grounding", "constraint_adherence", "no_hallucination"]}
        else:
            case_scores = score_planner_output(parsed, case["expected_fields"])

        mean = sum(case_scores.values()) / len(case_scores)
        all_scores.append(mean)
        results.append({
            "input": case["input"],
            "scores": case_scores,
            "mean": mean,
            "parsed": parsed.model_dump() if parsed else None,
        })

    overall_mean = sum(all_scores) / len(all_scores) if all_scores else 0.0
    return {"overall_mean": overall_mean, "cases": results, "threshold": 0.8}


def test_llm_judge_mean_score_above_threshold() -> None:
    """LLM-judge mean score across all test cases must be >= 0.8."""
    report = run_judge()
    print(f"\nLLM Judge overall mean: {report['overall_mean']:.3f}")
    for case in report["cases"]:
        print(f"  [{case['mean']:.2f}] {case['input'][:60]}")
        for dim, score in case["scores"].items():
            print(f"         {dim}: {score:.2f}")

    assert report["overall_mean"] >= report["threshold"], (
        f"LLM judge mean {report['overall_mean']:.3f} < threshold {report['threshold']}"
    )


if __name__ == "__main__":
    report = run_judge()
    print(json.dumps(report, indent=2, default=str))
    sys.exit(0 if report["overall_mean"] >= report["threshold"] else 1)

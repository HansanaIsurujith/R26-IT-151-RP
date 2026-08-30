import random

import pytest

from core.fuzzy_engine import (
    HAZARD_NAMES,
    evaluate_overall_risk,
    objective_linear_risk,
    weighted_fuzzy_or,
)
from core.objective_weighting import OBJECTIVE_WEIGHT_RESULT, OBJECTIVE_WEIGHTS


def risk(values):
    return evaluate_overall_risk(*values)["overall_risk_score"]


def test_critic_weights_are_reproducible_normalized_and_nonnegative():
    assert OBJECTIVE_WEIGHT_RESULT.method == "CRITIC"
    assert OBJECTIVE_WEIGHT_RESULT.row_count == 228
    assert len(OBJECTIVE_WEIGHT_RESULT.dataset_sha256) == 64
    assert set(OBJECTIVE_WEIGHTS) == set(HAZARD_NAMES)
    assert sum(OBJECTIVE_WEIGHTS.values()) == pytest.approx(1.0)
    assert all(value >= 0 for value in OBJECTIVE_WEIGHTS.values())


def test_required_boundaries_and_range():
    assert risk([0.0] * 6) == 0.0
    assert risk([1.0] * 6) == 1.0
    generator = random.Random(12)
    for _ in range(1000):
        score = risk([generator.random() for _ in range(6)])
        assert 0.0 <= score <= 1.0


@pytest.mark.parametrize("hazard_index", range(6))
def test_increasing_any_hazard_never_reduces_risk(hazard_index):
    generator = random.Random(100 + hazard_index)
    for _ in range(1000):
        before = [generator.random() for _ in range(6)]
        after = list(before)
        after[hazard_index] += generator.random() * (1.0 - before[hazard_index])
        assert risk(after) + 1e-10 >= risk(before)


def test_hierarchy_matches_direct_weighted_fuzzy_aggregation():
    values = [0.82, 0.1, 0.2, 0.05, 0.75, 0.4]
    direct = weighted_fuzzy_or(values, OBJECTIVE_WEIGHTS.values())
    assert risk(values) == pytest.approx(direct, abs=1e-6)


def test_proposed_operator_is_non_compensatory_relative_to_linear_baseline():
    scenarios = [
        [0.9, 0.1, 0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.95, 0.0, 0.05, 0.0],
        [0.2, 0.7, 0.1, 0.3, 0.2, 0.4],
    ]
    for values in scenarios:
        assert risk(values) + 1e-10 >= objective_linear_risk(*values)

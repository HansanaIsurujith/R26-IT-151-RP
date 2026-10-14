"""Objective-weighted monotonic hierarchical fuzzy hazard model.

This is the Option B decision model for the Suraksha Lanka routing component.
It does not use AHP questionnaires or simulated judges. Hazard weights are
derived reproducibly from the combined hazard dataset with CRITIC, while the
fuzzy aggregation satisfies safety properties that can be tested:

* range: every score is in [0, 1];
* boundary: all-zero hazards -> 0 and all-one hazards -> 1;
* monotonicity: increasing any single hazard can never reduce overall risk;
* non-compensation: one severe hazard is not cancelled by several low hazards.

Each normalized hazard value is interpreted as its fuzzy membership degree in
the set DANGEROUS (and 1-x in SAFE). Stages use a weighted probabilistic
fuzzy OR, implemented as the complement of a weighted geometric product:

    OR_w(x) = 1 - product((1 - x_i) ** normalized_weight_i)

Grouping environmental and wildlife hazards hierarchically is exactly
consistent with direct six-hazard aggregation when parent weights equal the
sum of child weights. This gives explainable intermediate scores without
changing the final mathematical result.
"""

from __future__ import annotations

import itertools
import math
import random
from typing import Iterable, Mapping

try:  # Package import (API/tests)
    from .objective_weighting import OBJECTIVE_WEIGHT_RESULT, OBJECTIVE_WEIGHTS
except ImportError:  # Direct execution
    from objective_weighting import OBJECTIVE_WEIGHT_RESULT, OBJECTIVE_WEIGHTS


HAZARD_NAMES = (
    "flood",
    "landslide",
    "elephant",
    "buffalo",
    "deer",
    "wildboar",
)

# Default decision-support profile. The benchmark script evaluates a complete
# lambda grid and reports sensitivity instead of claiming universal optimality.
LAMBDA_RISK_AVERSION = 8.0

LABEL_VALUES = {
    "NONE": 0.0,
    "LOW": 0.2,
    "MEDIUM": 0.5,
    "HIGH": 0.8,
    "CRITICAL": 1.0,
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def to_value(value: float | str) -> float:
    """Convert a normalized number or qualitative demo label to [0, 1]."""

    if isinstance(value, str):
        label = value.strip().upper()
        if label not in LABEL_VALUES:
            raise ValueError(
                f"Unknown hazard label {value!r}; choose from {list(LABEL_VALUES)}."
            )
        return LABEL_VALUES[label]
    return _clamp(value)


def fuzzify(value: float | str) -> dict[str, float]:
    """Return two complementary fuzzy memberships for a hazard signal."""

    dangerous = to_value(value)
    return {"safe": 1.0 - dangerous, "dangerous": dangerous}


def _normalise_weights(weights: Iterable[float]) -> list[float]:
    values = [max(0.0, float(weight)) for weight in weights]
    total = sum(values)
    if total <= 1e-15:
        return [1.0 / len(values)] * len(values) if values else []
    return [weight / total for weight in values]


def weighted_fuzzy_or(values: Iterable[float], weights: Iterable[float]) -> float:
    """Monotonic weighted fuzzy OR based on a product t-norm complement.

    Log-space computation is numerically stable for values close to one. A
    fully certain hazard (x=1) produces a fully dangerous result, provided its
    objective weight is positive.
    """

    crisp_values = [_clamp(value) for value in values]
    normalised = _normalise_weights(weights)
    if len(crisp_values) != len(normalised):
        raise ValueError("The number of fuzzy values and weights must match.")
    if not crisp_values:
        return 0.0

    log_safe_membership = 0.0
    for value, weight in zip(crisp_values, normalised):
        if weight <= 0.0:
            continue
        if value >= 1.0:
            return 1.0
        log_safe_membership += weight * math.log1p(-value)
    return _clamp(1.0 - math.exp(log_safe_membership))


def objective_linear_risk(
    flood_p: float | str,
    landslide_p: float | str,
    elephant_p: float | str,
    buffalo_p: float | str,
    deer_p: float | str,
    wildboar_p: float | str,
) -> float:
    """Return the compensatory CRITIC-weighted experimental baseline."""

    values = [
        to_value(value)
        for value in (
            flood_p,
            landslide_p,
            elephant_p,
            buffalo_p,
            deer_p,
            wildboar_p,
        )
    ]
    return _clamp(
        sum(
            OBJECTIVE_WEIGHTS[name] * value
            for name, value in zip(HAZARD_NAMES, values)
        )
    )


def _group_score(values: Mapping[str, float], names: tuple[str, ...]) -> float:
    return weighted_fuzzy_or(
        [values[name] for name in names],
        [OBJECTIVE_WEIGHTS[name] for name in names],
    )


def _group_weight(names: tuple[str, ...]) -> float:
    return sum(OBJECTIVE_WEIGHTS[name] for name in names)


def evaluate_overall_risk(
    flood_p: float | str,
    landslide_p: float | str,
    elephant_p: float | str,
    buffalo_p: float | str,
    deer_p: float | str,
    wildboar_p: float | str,
    verbose: bool = False,
) -> dict:
    """Evaluate all explainable stages of the six-hazard fuzzy hierarchy."""

    values = {
        name: to_value(value)
        for name, value in zip(
            HAZARD_NAMES,
            (flood_p, landslide_p, elephant_p, buffalo_p, deer_p, wildboar_p),
        )
    }

    environmental_names = ("flood", "landslide")
    large_mammal_names = ("elephant", "buffalo")
    small_mammal_names = ("deer", "wildboar")

    environmental = _group_score(values, environmental_names)
    large_mammal = _group_score(values, large_mammal_names)
    small_mammal = _group_score(values, small_mammal_names)

    large_weight = _group_weight(large_mammal_names)
    small_weight = _group_weight(small_mammal_names)
    wildlife = weighted_fuzzy_or(
        [large_mammal, small_mammal], [large_weight, small_weight]
    )

    environmental_weight = _group_weight(environmental_names)
    wildlife_weight = large_weight + small_weight
    overall = weighted_fuzzy_or(
        [environmental, wildlife], [environmental_weight, wildlife_weight]
    )
    linear_baseline = objective_linear_risk(
        values["flood"],
        values["landslide"],
        values["elephant"],
        values["buffalo"],
        values["deer"],
        values["wildboar"],
    )

    result = {
        "flood_p": values["flood"],
        "landslide_p": values["landslide"],
        "elephant_p": values["elephant"],
        "buffalo_p": values["buffalo"],
        "deer_p": values["deer"],
        "wildboar_p": values["wildboar"],
        "environmental_risk_score": round(environmental, 6),
        "large_mammal_risk_score": round(large_mammal, 6),
        "small_mammal_risk_score": round(small_mammal, 6),
        "wildlife_risk_score": round(wildlife, 6),
        "objective_linear_score": round(linear_baseline, 6),
        "overall_risk_score": round(overall, 6),
        "weighting_method": OBJECTIVE_WEIGHT_RESULT.method,
    }
    if verbose:
        for name in HAZARD_NAMES:
            print(
                f"  {name:<10} {fuzzify(values[name])} "
                f"weight={OBJECTIVE_WEIGHTS[name]:.4f}"
            )
        print(f"  environmental={environmental:.6f}")
        print(f"  wildlife={wildlife:.6f}")
        print(f"  linear baseline={linear_baseline:.6f}")
        print(f"  monotonic fuzzy overall={overall:.6f}")
    return result


def segment_cost(
    travel_time_minutes: float,
    flood_p: float | str,
    landslide_p: float | str,
    elephant_p: float | str,
    buffalo_p: float | str,
    deer_p: float | str,
    wildboar_p: float | str,
    lam: float | None = None,
) -> tuple[float, float]:
    """Return cost = time * (1 + lambda * objective_fuzzy_risk)."""

    risk_aversion = LAMBDA_RISK_AVERSION if lam is None else max(0.0, float(lam))
    risk = evaluate_overall_risk(
        flood_p,
        landslide_p,
        elephant_p,
        buffalo_p,
        deer_p,
        wildboar_p,
    )["overall_risk_score"]
    return float(travel_time_minutes) * (1.0 + risk_aversion * risk), risk


def monotonicity_audit(samples: int = 10_000, seed: int = 2026) -> dict:
    """Run a reproducible monotonicity property audit."""

    generator = random.Random(seed)
    violations = 0
    largest_drop = 0.0
    for _ in range(samples):
        base = [generator.random() for _ in HAZARD_NAMES]
        changed_index = generator.randrange(len(HAZARD_NAMES))
        increased = list(base)
        increased[changed_index] = base[changed_index] + generator.random() * (
            1.0 - base[changed_index]
        )
        before = evaluate_overall_risk(*base)["overall_risk_score"]
        after = evaluate_overall_risk(*increased)["overall_risk_score"]
        drop = before - after
        if drop > 1e-10:
            violations += 1
            largest_drop = max(largest_drop, drop)
    return {
        "samples": samples,
        "seed": seed,
        "violations": violations,
        "largest_drop": largest_drop,
        "passed": violations == 0,
    }


def run_64_scenario_demo() -> None:
    """Print all binary combinations for transparent model inspection."""

    print("scenario  env       wildlife  linear    fuzzy")
    for combination in itertools.product([0.0, 1.0], repeat=6):
        result = evaluate_overall_risk(*combination)
        label = "".join(str(int(value)) for value in combination)
        print(
            f"{label:<10}{result['environmental_risk_score']:<10.4f}"
            f"{result['wildlife_risk_score']:<10.4f}"
            f"{result['objective_linear_score']:<10.4f}"
            f"{result['overall_risk_score']:<10.4f}"
        )


if __name__ == "__main__":
    print("OBJECTIVE-WEIGHTED MONOTONIC HIERARCHICAL FUZZY MODEL")
    print("CRITIC weights:")
    for hazard, weight in OBJECTIVE_WEIGHTS.items():
        print(f"  {hazard:<10} {weight:.6f}")
    print("\nExample trace:")
    evaluate_overall_risk(0.82, 0.10, 0.20, 0.05, 0.75, 0.40, verbose=True)
    print("\nMonotonicity audit:", monotonicity_audit())

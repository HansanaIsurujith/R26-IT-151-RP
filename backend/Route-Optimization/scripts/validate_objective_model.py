"""Validate mathematical properties and CRITIC weight stability.

The generated report is objective internal validation. It deliberately does
not use simulated judges or describe itself as external route accuracy.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


COMPONENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COMPONENT_ROOT))

from core.fuzzy_engine import (  # noqa: E402
    evaluate_overall_risk,
    monotonicity_audit,
    weighted_fuzzy_or,
)
from core.objective_weighting import (  # noqa: E402
    DEFAULT_DATASET,
    HAZARD_COLUMNS,
    OBJECTIVE_WEIGHT_RESULT,
    _read_hazard_matrix,
)


def critic_from_matrix(matrix):
    contrast = np.std(matrix, axis=0, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        correlation = np.corrcoef(matrix, rowvar=False)
    correlation = np.nan_to_num(correlation, nan=0.0, posinf=0.0, neginf=0.0)
    information = contrast * np.sum(1.0 - np.clip(correlation, -1, 1), axis=1)
    if information.sum() <= 1e-12:
        return np.full(matrix.shape[1], 1.0 / matrix.shape[1])
    return information / information.sum()


def bootstrap_weight_stability(matrix, iterations, seed):
    generator = np.random.default_rng(seed)
    samples = np.empty((iterations, matrix.shape[1]), dtype=float)
    for index in range(iterations):
        selected = generator.integers(0, matrix.shape[0], size=matrix.shape[0])
        samples[index] = critic_from_matrix(matrix[selected])
    names = list(HAZARD_COLUMNS)
    result = {}
    for column, name in enumerate(names):
        result[name] = {
            "mean": round(float(samples[:, column].mean()), 8),
            "std": round(float(samples[:, column].std(ddof=1)), 8),
            "ci95_low": round(float(np.quantile(samples[:, column], 0.025)), 8),
            "ci95_high": round(float(np.quantile(samples[:, column], 0.975)), 8),
            "top_rank_frequency": round(
                float(np.mean(np.argmax(samples, axis=1) == column)), 4
            ),
        }
    return result


def hierarchy_equivalence(samples, seed):
    generator = np.random.default_rng(seed)
    weights = list(OBJECTIVE_WEIGHT_RESULT.weights.values())
    maximum_error = 0.0
    for values in generator.random((samples, 6)):
        hierarchical = evaluate_overall_risk(*values)["overall_risk_score"]
        direct = weighted_fuzzy_or(values, weights)
        maximum_error = max(maximum_error, abs(hierarchical - direct))
    return {
        "samples": samples,
        "maximum_absolute_error": maximum_error,
        "passed": maximum_error <= 1e-6,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap-iterations", type=int, default=1000)
    parser.add_argument("--monotonicity-samples", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument(
        "--output",
        type=Path,
        default=COMPONENT_ROOT / "results" / "model_validation.json",
    )
    args = parser.parse_args()

    matrix = _read_hazard_matrix(DEFAULT_DATASET)
    zero_score = evaluate_overall_risk(*([0.0] * 6))["overall_risk_score"]
    one_score = evaluate_overall_risk(*([1.0] * 6))["overall_risk_score"]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_design": "Option B: objective weighting without human surveys",
        "weighting_provenance": OBJECTIVE_WEIGHT_RESULT.as_dict(),
        "boundary_tests": {
            "all_zero": zero_score,
            "all_one": one_score,
            "passed": zero_score == 0.0 and one_score == 1.0,
        },
        "monotonicity": monotonicity_audit(
            samples=args.monotonicity_samples, seed=args.seed
        ),
        "hierarchy_equivalence": hierarchy_equivalence(10000, args.seed),
        "bootstrap_weight_stability": {
            "iterations": args.bootstrap_iterations,
            "seed": args.seed,
            "hazards": bootstrap_weight_stability(
                matrix, args.bootstrap_iterations, args.seed
            ),
        },
        "claim_boundary": (
            "These tests establish reproducibility, stability and internal validity. "
            "They do not establish 100 percent real-world accuracy or road safety."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as target:
        json.dump(report, target, indent=2)
        target.write("\n")
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()

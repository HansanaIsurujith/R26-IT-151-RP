"""Run a reproducible route benchmark for the Option B research model.

This experiment compares the same origin-destination pairs under:

* shortest_path (travel-time baseline)
* objective_weight (CRITIC linear baseline)
* objective_fuzzy (proposed monotonic fuzzy model)

It measures exposure reduction, time overhead, severe sections and Pareto
success. It does not call these values prediction accuracy or human ground
truth because no observed correct-route labels are available.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


COMPONENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COMPONENT_ROOT))

from core.objective_weighting import OBJECTIVE_WEIGHT_RESULT  # noqa: E402
from core.routing_engine import (  # noqa: E402
    HAZARD_ATTRS,
    find_route,
    get_travel_time,
    get_node_coordinates,
    haversine_km,
    invalidate_edge_risk_cache,
    load_network,
    precompute_objective_risks,
    select_edge_data,
)


DEFAULT_NETWORK = (
    COMPONENT_ROOT / "network" / "gampaha_road_network_with_hazards.graphml"
)
DEFAULT_OUTPUT = COMPONENT_ROOT / "results"
METHODS = ("shortest_path", "objective_weight", "objective_fuzzy")
DEFAULT_LAMBDA = 8.0


def as_float(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def edge_records(graph):
    """Return stable edge references whose dictionaries can be safely restored."""

    if graph.is_multigraph():
        return list(graph.edges(keys=True, data=True))
    return [(source, target, None, data) for source, target, data in graph.edges(data=True)]


def independent_route_metrics(graph, result):
    """Evaluate a route directly on raw hazards, independent of its objective."""

    exposures = {attribute: 0.0 for attribute in HAZARD_ATTRS}
    total_time = 0.0
    high_zone_time = 0.0
    maximum_raw_hazard = 0.0
    for source, target in zip(result["path"][:-1], result["path"][1:]):
        data = select_edge_data(
            graph,
            source,
            target,
            method=result["method"],
            lam=result["risk_aversion"],
        )
        duration = get_travel_time(data)
        values = {attribute: as_float(data.get(attribute, 0.0)) for attribute in HAZARD_ATTRS}
        segment_maximum = max(values.values())
        total_time += duration
        maximum_raw_hazard = max(maximum_raw_hazard, segment_maximum)
        if segment_maximum >= 0.7:
            high_zone_time += duration
        for attribute, value in values.items():
            exposures[attribute] += duration * value
    metrics = {
        "maximum_raw_hazard": round(maximum_raw_hazard, 6),
        "high_risk_zone_time_pct": round(high_zone_time / max(total_time, 1e-12) * 100.0, 6),
        "raw_total_exposure": round(sum(exposures.values()), 6),
    }
    for attribute, exposure in exposures.items():
        short_name = attribute.replace("_probability", "").replace("_risk", "")
        metrics[f"raw_{short_name}_exposure"] = round(exposure, 6)
        metrics[f"raw_{short_name}_mean"] = round(exposure / max(total_time, 1e-12), 6)
    return metrics


def bootstrap_mean_ci(values, seed, samples=5_000):
    if not values:
        return {"mean": 0.0, "ci95_low": 0.0, "ci95_high": 0.0}
    generator = random.Random(seed)
    estimates = sorted(
        mean([values[generator.randrange(len(values))] for _ in values])
        for _ in range(samples)
    )
    low = estimates[int(0.025 * (samples - 1))]
    high = estimates[int(0.975 * (samples - 1))]
    return {
        "mean": round(mean(values), 6),
        "ci95_low": round(low, 6),
        "ci95_high": round(high, 6),
    }


def paired_standardized_effect(differences):
    if len(differences) < 2:
        return 0.0
    deviation = statistics.stdev(differences)
    return round(mean(differences) / deviation, 6) if deviation > 1e-12 else 0.0


def path_edge_set(path):
    return set(zip(path[:-1], path[1:]))


def path_jaccard(first, second):
    first_edges = path_edge_set(first)
    second_edges = path_edge_set(second)
    union = first_edges | second_edges
    return len(first_edges & second_edges) / len(union) if union else 1.0


def mean(values):
    return statistics.fmean(values) if values else 0.0


def pct_change(value, baseline):
    if baseline <= 1e-12:
        return 0.0
    return (value - baseline) / baseline * 100.0


def guarded_route(graph, source, target, fastest, method, requested_lambda, max_detour=30.0):
    """Mirror the API's deterministic per-route detour guardrail."""

    if method == "shortest_path":
        return fastest, False
    requested = find_route(
        graph, source, target, method=method, lam=requested_lambda
    )
    if requested is None:
        return None, False
    if pct_change(requested["total_time_min"], fastest["total_time_min"]) <= max_detour:
        return requested, False
    candidates = [requested]
    for step in range(7):
        candidate_lambda = float(requested_lambda) * step / 6.0
        if abs(candidate_lambda - float(requested_lambda)) < 1e-9:
            continue
        candidate = find_route(
            graph, source, target, method=method, lam=candidate_lambda
        )
        if candidate is not None:
            candidates.append(candidate)
    feasible = [
        candidate
        for candidate in candidates
        if pct_change(candidate["total_time_min"], fastest["total_time_min"])
        <= max_detour + 1e-9
    ]
    if not feasible:
        return fastest, True
    return min(
        feasible,
        key=lambda candidate: (
            candidate["time_weighted_risk_exposure"],
            candidate["total_time_min"],
        ),
    ), True


def candidate_nodes(graph):
    """Use nodes in the measured grid extent to avoid overstating coverage."""

    selected = []
    for node in graph.nodes:
        latitude, longitude = get_node_coordinates(graph, node)
        if 6.89 <= latitude <= 7.16 and 79.84 <= longitude <= 80.21:
            selected.append(node)
    return selected or list(graph.nodes)


def sample_pairs(graph, count, seed):
    generator = random.Random(seed)
    nodes = candidate_nodes(graph)
    pairs = []
    seen = set()
    attempts = 0
    while len(pairs) < count and attempts < count * 100:
        attempts += 1
        source, target = generator.sample(nodes, 2)
        key = (str(source), str(target))
        if key in seen:
            continue
        source_lat, source_lon = get_node_coordinates(graph, source)
        target_lat, target_lon = get_node_coordinates(graph, target)
        straight_line = haversine_km(
            source_lat, source_lon, target_lat, target_lon
        )
        if straight_line < 5.0 or straight_line > 35.0:
            continue
        fastest = find_route(graph, source, target, method="shortest_path", lam=0)
        if fastest is None:
            continue
        seen.add(key)
        pairs.append((source, target, fastest, straight_line))
    if len(pairs) < count:
        raise RuntimeError(
            f"Only {len(pairs)} connected OD pairs were found after {attempts} attempts."
        )
    return pairs


def benchmark(graph, pairs, lambdas):
    rows = []
    for pair_index, (source, target, fastest, straight_line) in enumerate(
        pairs, start=1
    ):
        for risk_aversion in lambdas:
            results = {"shortest_path": fastest}
            guardrail_flags = {"shortest_path": False}
            for method in METHODS[1:]:
                results[method], guardrail_flags[method] = guarded_route(
                    graph, source, target, fastest, method, risk_aversion
                )
            for method in METHODS:
                result = results[method]
                if result is None:
                    continue
                risk_reduction = -pct_change(
                    result["time_weighted_risk_exposure"],
                    fastest["time_weighted_risk_exposure"],
                )
                time_overhead = pct_change(
                    result["total_time_min"], fastest["total_time_min"]
                )
                rows.append(
                    {
                        "pair_id": pair_index,
                        "source_node": str(source),
                        "target_node": str(target),
                        "straight_line_km": round(straight_line, 3),
                        "lambda": risk_aversion,
                        "effective_lambda": result["risk_aversion"],
                        "guardrail_applied": guardrail_flags[method],
                        "method": method,
                        "duration_min": result["total_time_min"],
                        "distance_km": result["total_distance_km"],
                        "mean_risk": result["normalized_risk_score"],
                        "risk_exposure": result["time_weighted_risk_exposure"],
                        "maximum_segment_risk": result["maximum_segment_risk"],
                        "high_risk_segments": result["high_risk_segments"],
                        "risk_reduction_vs_fastest_pct": round(risk_reduction, 4),
                        "time_overhead_vs_fastest_pct": round(time_overhead, 4),
                        "pareto_success_under_30pct_detour": (
                            method != "shortest_path"
                            and risk_reduction > 0.0
                            and time_overhead <= 30.0
                        ),
                        **independent_route_metrics(graph, result),
                    }
                )
        print(f"Completed OD pair {pair_index}/{len(pairs)}")
    return rows


def base_fuzzy_results(graph, pairs, risk_aversion):
    return {
        pair_index: guarded_route(
            graph, source, target, fastest, "objective_fuzzy", risk_aversion
        )[0]
        for pair_index, (source, target, fastest, _distance) in enumerate(
            pairs, start=1
        )
    }


def set_edge_hazards(records, transform):
    """Apply a reversible transformation to all six raw hazard attributes."""

    saved = []
    for source, target, key, data in records:
        original = {attribute: data.get(attribute, 0.0) for attribute in HAZARD_ATTRS}
        saved.append((data, original))
        transformed = transform(source, target, key, original)
        for attribute, value in transformed.items():
            data[attribute] = float(value)
        invalidate_edge_risk_cache(data)
    return saved


def restore_edge_hazards(saved):
    for data, original in saved:
        for attribute, value in original.items():
            data[attribute] = value
        invalidate_edge_risk_cache(data)


def ablation_experiment(graph, records, pairs, base_results, risk_aversion):
    """Remove one hazard at a time, reroute, then evaluate on complete raw data."""

    results = []
    for removed_attribute in HAZARD_ATTRS:
        saved = set_edge_hazards(
            records,
            lambda _u, _v, _key, original: {
                attribute: (0.0 if attribute == removed_attribute else as_float(value))
                for attribute, value in original.items()
            },
        )
        ablated_routes = {
            pair_index: guarded_route(
                graph, source, target, fastest, "objective_fuzzy", risk_aversion
            )[0]
            for pair_index, (source, target, fastest, _distance) in enumerate(
                pairs, start=1
            )
        }
        restore_edge_hazards(saved)
        precompute_objective_risks(graph)

        exposure_changes = []
        omitted_hazard_changes = []
        changed = 0
        short_name = removed_attribute.replace("_probability", "").replace("_risk", "")
        for pair_index, base in base_results.items():
            ablated = ablated_routes[pair_index]
            if not base or not ablated:
                continue
            changed += ablated["path"] != base["path"]
            base_metrics = independent_route_metrics(graph, base)
            ablated_metrics = independent_route_metrics(graph, ablated)
            exposure_changes.append(
                pct_change(
                    ablated_metrics["raw_total_exposure"],
                    base_metrics["raw_total_exposure"],
                )
            )
            omitted_hazard_changes.append(
                pct_change(
                    ablated_metrics[f"raw_{short_name}_exposure"],
                    base_metrics[f"raw_{short_name}_exposure"],
                )
            )
        count = max(1, len(exposure_changes))
        results.append(
            {
                "removed_hazard": short_name,
                "pairs": len(exposure_changes),
                "route_changed_pct": round(changed / count * 100.0, 4),
                "mean_full_raw_exposure_change_pct": round(mean(exposure_changes), 4),
                "mean_removed_hazard_exposure_change_pct": round(
                    mean(omitted_hazard_changes), 4
                ),
            }
        )
        print(f"Completed ablation: {short_name}")
    return results


def held_out_location_experiment(
    graph, records, pairs, base_results, risk_aversion, holdout_fraction=0.2
):
    """Hide deterministic spatial cells during routing and evaluate on full data."""

    def mask_spatial_cell(source, target, _key, original):
        source_lat, source_lon = get_node_coordinates(graph, source)
        target_lat, target_lon = get_node_coordinates(graph, target)
        cell = f"{(source_lat + target_lat) / 2:.2f}:{(source_lon + target_lon) / 2:.2f}"
        bucket = int(hashlib.sha256(cell.encode("utf-8")).hexdigest()[:8], 16) % 10_000
        held_out = bucket < int(holdout_fraction * 10_000)
        return {
            attribute: (0.0 if held_out else as_float(value))
            for attribute, value in original.items()
        }

    saved = set_edge_hazards(records, mask_spatial_cell)
    heldout_routes = {
        pair_index: guarded_route(
            graph, source, target, fastest, "objective_fuzzy", risk_aversion
        )[0]
        for pair_index, (source, target, fastest, _distance) in enumerate(
            pairs, start=1
        )
    }
    restore_edge_hazards(saved)
    precompute_objective_risks(graph)

    exposure_changes = []
    overlaps = []
    changed = 0
    for pair_index, base in base_results.items():
        heldout = heldout_routes[pair_index]
        if not base or not heldout:
            continue
        changed += heldout["path"] != base["path"]
        overlaps.append(path_jaccard(base["path"], heldout["path"]))
        base_metrics = independent_route_metrics(graph, base)
        heldout_metrics = independent_route_metrics(graph, heldout)
        exposure_changes.append(
            pct_change(
                heldout_metrics["raw_total_exposure"],
                base_metrics["raw_total_exposure"],
            )
        )
    count = max(1, len(exposure_changes))
    return {
        "design": "20% deterministic spatial cells hidden during route selection",
        "holdout_fraction": holdout_fraction,
        "pairs": len(exposure_changes),
        "route_changed_pct": round(changed / count * 100.0, 4),
        "mean_path_jaccard": round(mean(overlaps), 6),
        "full_data_raw_exposure_change_pct": bootstrap_mean_ci(
            exposure_changes, seed=20261
        ),
    }


def stability_experiment(
    graph, records, pairs, base_results, risk_aversion, trials, epsilon
):
    """Perturb each raw hazard slightly and report path/risk sensitivity."""

    overlaps = []
    exposure_changes = []
    changed = 0
    comparisons = 0
    for trial in range(trials):
        generator = random.Random(50_000 + trial)

        def perturb(_source, _target, _key, original):
            return {
                attribute: max(
                    0.0,
                    min(1.0, as_float(value) + generator.uniform(-epsilon, epsilon)),
                )
                for attribute, value in original.items()
            }

        saved = set_edge_hazards(records, perturb)
        perturbed_routes = {
            pair_index: guarded_route(
                graph, source, target, fastest, "objective_fuzzy", risk_aversion
            )[0]
            for pair_index, (source, target, fastest, _distance) in enumerate(
                pairs, start=1
            )
        }
        restore_edge_hazards(saved)
        precompute_objective_risks(graph)
        for pair_index, base in base_results.items():
            perturbed = perturbed_routes[pair_index]
            if not base or not perturbed:
                continue
            comparisons += 1
            changed += perturbed["path"] != base["path"]
            overlaps.append(path_jaccard(base["path"], perturbed["path"]))
            base_metrics = independent_route_metrics(graph, base)
            perturbed_metrics = independent_route_metrics(graph, perturbed)
            exposure_changes.append(
                pct_change(
                    perturbed_metrics["raw_total_exposure"],
                    base_metrics["raw_total_exposure"],
                )
            )
        print(f"Completed stability trial {trial + 1}/{trials}")
    return {
        "perturbation": f"independent uniform +/- {epsilon:.3f} per raw hazard",
        "trials": trials,
        "route_comparisons": comparisons,
        "route_changed_pct": round(changed / max(1, comparisons) * 100.0, 4),
        "mean_path_jaccard": round(mean(overlaps), 6),
        "full_data_raw_exposure_change_pct": bootstrap_mean_ci(
            exposure_changes, seed=20262
        ),
    }


def summarize(rows, pair_count, seed, network_path):
    groups = {}
    for row in rows:
        key = (row["method"], row["lambda"])
        groups.setdefault(key, []).append(row)

    summaries = []
    for (method, risk_aversion), group in sorted(groups.items()):
        reductions = [row["risk_reduction_vs_fastest_pct"] for row in group]
        overheads = [row["time_overhead_vs_fastest_pct"] for row in group]
        summaries.append(
            {
                "method": method,
                "lambda": risk_aversion,
                "trips": len(group),
                "mean_duration_min": round(
                    mean([row["duration_min"] for row in group]), 4
                ),
                "mean_risk": round(mean([row["mean_risk"] for row in group]), 6),
                "mean_exposure_reduction_pct": round(mean(reductions), 4),
                "median_exposure_reduction_pct": round(
                    statistics.median(reductions), 4
                ),
                "mean_time_overhead_pct": round(mean(overheads), 4),
                "maximum_time_overhead_pct": round(max(overheads), 4),
                "guardrail_applied_pct": round(
                    sum(row["guardrail_applied"] for row in group)
                    / len(group)
                    * 100.0,
                    2,
                ),
                "trips_with_lower_exposure_pct": round(
                    sum(value > 0 for value in reductions) / len(group) * 100.0, 2
                ),
                "pareto_success_under_30pct_detour_pct": round(
                    sum(row["pareto_success_under_30pct_detour"] for row in group)
                    / len(group)
                    * 100.0,
                    2,
                ),
            }
        )

    paired_comparisons = []
    for risk_aversion in sorted({row["lambda"] for row in rows}):
        by_key = {
            (row["pair_id"], row["method"]): row
            for row in rows
            if row["lambda"] == risk_aversion
        }
        relative_improvements = []
        duration_changes = []
        wins = losses = ties = 0
        for pair_id in sorted({row["pair_id"] for row in rows}):
            fuzzy = by_key.get((pair_id, "objective_fuzzy"))
            linear = by_key.get((pair_id, "objective_weight"))
            if not fuzzy or not linear:
                continue
            difference = linear["risk_exposure"] - fuzzy["risk_exposure"]
            if difference > 1e-6:
                wins += 1
            elif difference < -1e-6:
                losses += 1
            else:
                ties += 1
            if linear["risk_exposure"] > 1e-12:
                relative_improvements.append(
                    difference / linear["risk_exposure"] * 100.0
                )
            duration_changes.append(
                pct_change(fuzzy["duration_min"], linear["duration_min"])
            )
        non_ties = wins + losses
        smaller_side = min(wins, losses)
        if non_ties:
            sign_probability = min(
                1.0,
                2.0
                * sum(math.comb(non_ties, value) for value in range(smaller_side + 1))
                / (2**non_ties),
            )
        else:
            sign_probability = 1.0
        paired_comparisons.append(
            {
                "lambda": risk_aversion,
                "pairs": wins + losses + ties,
                "objective_fuzzy_lower_exposure": wins,
                "objective_fuzzy_higher_exposure": losses,
                "same_exposure": ties,
                "mean_exposure_improvement_vs_linear_pct": round(
                    mean(relative_improvements), 4
                ),
                "median_exposure_improvement_vs_linear_pct": round(
                    statistics.median(relative_improvements), 4
                ),
                "mean_time_change_vs_linear_pct": round(
                    mean(duration_changes), 4
                ),
                "exact_two_sided_sign_test_p": round(sign_probability, 6),
            }
        )

    independent_effects = []
    for risk_aversion in sorted({row["lambda"] for row in rows}):
        by_key = {
            (row["pair_id"], row["method"]): row
            for row in rows
            if row["lambda"] == risk_aversion
        }
        for baseline_method in ("shortest_path", "objective_weight"):
            raw_changes = []
            maximum_changes = []
            high_zone_changes = []
            for pair_id in sorted({row["pair_id"] for row in rows}):
                fuzzy = by_key.get((pair_id, "objective_fuzzy"))
                baseline = by_key.get((pair_id, baseline_method))
                if not fuzzy or not baseline:
                    continue
                raw_changes.append(
                    pct_change(
                        fuzzy["raw_total_exposure"], baseline["raw_total_exposure"]
                    )
                )
                maximum_changes.append(
                    fuzzy["maximum_raw_hazard"] - baseline["maximum_raw_hazard"]
                )
                high_zone_changes.append(
                    fuzzy["high_risk_zone_time_pct"]
                    - baseline["high_risk_zone_time_pct"]
                )
            independent_effects.append(
                {
                    "lambda": risk_aversion,
                    "comparison": f"objective_fuzzy_vs_{baseline_method}",
                    "pairs": len(raw_changes),
                    "raw_total_exposure_change_pct": bootstrap_mean_ci(
                        raw_changes, seed + int(risk_aversion * 10)
                    ),
                    "paired_standardized_effect_dz": paired_standardized_effect(
                        [-value for value in raw_changes]
                    ),
                    "maximum_raw_hazard_change": bootstrap_mean_ci(
                        maximum_changes, seed + 101
                    ),
                    "high_risk_zone_time_change_percentage_points": bootstrap_mean_ci(
                        high_zone_changes, seed + 202
                    ),
                }
            )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_design": "Option B: no human-response dependency",
        "claim_boundary": (
            "Internal comparative benchmark on available hazard proxies; "
            "not perfect real-world accuracy and not observed route ground truth."
        ),
        "network": str(network_path),
        "od_pairs": pair_count,
        "seed": seed,
        "weighting": OBJECTIVE_WEIGHT_RESULT.as_dict(),
        "metrics": {
            "optimization_metric": "time_weighted_objective_fuzzy_risk_exposure",
            "independent_evaluation_metrics": [
                "six raw hazard exposures",
                "maximum raw hazard on any segment",
                "percentage of travel time in raw high-risk zones",
                "travel-time overhead",
                "held-out spatial-cell performance",
                "route stability under small raw-input perturbations",
            ],
            "efficiency_metric": "travel_time_overhead_vs_fastest",
            "guardrail": "maximum 30 percent travel-time detour",
        },
        "summary_by_method_and_lambda": summaries,
        "paired_objective_fuzzy_vs_linear": paired_comparisons,
        "independent_paired_effects_with_95pct_bootstrap_ci": independent_effects,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", type=Path, default=DEFAULT_NETWORK)
    parser.add_argument("--pairs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--lambdas", default="2,4,8,12")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--stability-trials", type=int, default=2)
    parser.add_argument("--stability-epsilon", type=float, default=0.025)
    parser.add_argument(
        "--skip-robustness",
        action="store_true",
        help="Skip held-out, perturbation and ablation experiments for a quick smoke run.",
    )
    args = parser.parse_args()
    lambdas = [float(value) for value in args.lambdas.split(",")]
    if args.pairs < 2:
        raise SystemExit("--pairs must be at least 2")

    started = time.perf_counter()
    graph = load_network(args.network)
    cached = precompute_objective_risks(graph)
    print(f"Prepared {cached} edge risk scores")
    pairs = sample_pairs(graph, args.pairs, args.seed)
    rows = benchmark(graph, pairs, lambdas)
    summary = summarize(rows, len(pairs), args.seed, args.network)
    if not args.skip_robustness:
        analysis_lambda = min(lambdas, key=lambda value: abs(value - DEFAULT_LAMBDA))
        records = edge_records(graph)
        base_results = base_fuzzy_results(graph, pairs, analysis_lambda)
        summary["robustness_analysis_lambda"] = analysis_lambda
        summary["held_out_location_evaluation"] = held_out_location_experiment(
            graph, records, pairs, base_results, analysis_lambda
        )
        summary["input_perturbation_stability"] = stability_experiment(
            graph,
            records,
            pairs,
            base_results,
            analysis_lambda,
            max(1, args.stability_trials),
            max(0.001, min(0.1, args.stability_epsilon)),
        )
        summary["leave_one_hazard_out_ablation"] = ablation_experiment(
            graph, records, pairs, base_results, analysis_lambda
        )
    summary["runtime_seconds"] = round(time.perf_counter() - started, 3)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "objective_route_benchmark.csv"
    json_path = args.output_dir / "objective_route_benchmark_summary.json"
    with csv_path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with json_path.open("w", encoding="utf-8") as target:
        json.dump(summary, target, indent=2)
        target.write("\n")
    print(f"Saved {csv_path}")
    print(f"Saved {json_path}")


if __name__ == "__main__":
    main()

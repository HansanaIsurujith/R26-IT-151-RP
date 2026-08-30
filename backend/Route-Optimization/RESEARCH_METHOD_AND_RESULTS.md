# Research Method and Measured Results

## Final title

Objective-Weighted Monotonic Hierarchical Fuzzy Multi-Hazard Risk-Aware
Routing for the Gampaha Road Network

## Component in one sentence

Given simultaneous flood, landslide and wildlife risk signals, the component
chooses a road route that balances travel time and hazard exposure, then
compares that decision with simpler baselines on the same real road network.

## Research gap

Hazard detection answers what is dangerous and where. It does not directly
answer what a traveller should do when different hazards occur together and a
safer detour costs additional time. This component studies that downstream
multi-criteria decision problem.

## Research questions

1. Can objective, data-derived criterion weights replace unavailable or
   unreliable human pairwise responses?
2. Can a hierarchical fuzzy operator combine six hazards while guaranteeing
   that increasing a hazard never lowers road risk?
3. Does the proposed route reduce time-weighted hazard exposure compared with
   the fastest route and an objective linear baseline under a detour constraint?

## Option B methodology

### Objective weights

CRITIC derives criterion importance from contrast and correlation in the
228-row combined hazard grid:

~~~text
C_j = sigma_j × sum_k(1 - r_jk)
w_j = C_j / sum(C)
~~~

Current weights:

| Flood | Landslide | Elephant | Buffalo | Deer | Wild boar |
|---:|---:|---:|---:|---:|---:|
| 0.354526 | 0.283204 | 0.048109 | 0.095989 | 0.118132 | 0.100040 |

These weights describe information contrast and non-redundancy in this
dataset. They must not be interpreted as clinical or social severity.

### Proposed monotonic fuzzy decision model

Each normalized signal is a fuzzy degree of membership in DANGEROUS. The
weighted product-complement fuzzy OR is:

~~~text
R = 1 - product((1 - x_i) ^ w_i)
~~~

This operator is bounded, has correct zero/one boundaries, is
non-compensatory and is monotonic in every input. The hierarchy exposes
environmental, large-mammal, small-mammal and wildlife intermediate scores
while remaining equivalent to direct six-hazard aggregation.

### Route objective

~~~text
C(e) = T(e) × [1 + lambda × R(e)]
~~~

The API has a 30% travel-time detour guardrail. If a requested lambda would
exceed it, deterministic sensitivity candidates are evaluated and the
lowest-exposure feasible candidate is returned.

### Baselines

| Method | Meaning |
|---|---|
| shortest_path | A-star minimizing travel time only |
| objective_weight | A-star using a compensatory CRITIC linear risk |
| objective_fuzzy | Proposed non-compensatory monotonic fuzzy risk |

The proposed fuzzy exposure is reported as the optimization-scale metric, but
the final evaluation is not circular: routes are also evaluated with raw
per-hazard exposures, maximum raw segment hazard, percentage of travel time in
raw high-risk zones, held-out spatial cells and perturbation stability.

This is a fuzzy aggregation operator, not a traditional Mamdani rule-based
inference system. The final method does not use human pairwise questionnaires.

## Internal model validation

Saved report: results/model_validation.json

| Check | Result |
|---|---:|
| All-zero boundary | 0.0 |
| All-one boundary | 1.0 |
| Random monotonicity checks | 100,000 |
| Monotonicity violations | 0 |
| Hierarchy-equivalence checks | 10,000 passed |
| CRITIC bootstrap resamples | 1,000 |
| Flood top-ranked bootstrap frequency | 99.2% |

The 95% bootstrap intervals are stored for every weight with the fixed seed
and source dataset checksum.

## Real-network paired benchmark

Saved files:

- results/objective_route_benchmark.csv
- results/objective_route_benchmark_summary.json

Design:

- real Gampaha OSM network: 73,603 nodes and 165,094 edges;
- 100 connected origin-destination pairs sampled with seed 2026;
- straight-line trip range: 5 to 35 km;
- requested lambda: 8, with the same deterministic per-route guardrail used by
  the API;
- 300 guarded method-trip records;
- independent outcomes: six raw hazard exposures, maximum raw hazard, raw
  high-risk-zone time and travel-time overhead;
- robustness: 20% deterministic spatial-cell holdout, two small-input
  perturbation trials and six leave-one-hazard-out ablations;
- uncertainty: 5,000-resample paired bootstrap confidence intervals and paired
  standardized effect sizes.

### Proposed model versus fastest route

| Method | Mean fuzzy-exposure reduction | Mean time overhead | Maximum overhead | Lower-exposure trips | Guardrail adjusted |
|---|---:|---:|---:|---:|---:|
| Risk-Aware fuzzy | 24.36% | 7.12% | 29.34% | 59% | 47% |
| Objective linear | 23.97% | 6.33% | 29.34% | 57% | 30% |
| Fastest | Reference | 0.00% | 0.00% | Reference | 0% |

The maximum observed overhead stayed below 30% because every experimental
route used the production guardrail. The adjustment rate shows why reporting a
sample-average detour alone would have been insufficient.

### Independent raw outcomes

Compared with Fastest, the proposed route changed unweighted total raw hazard
exposure by **-14.60%** (95% bootstrap CI **-18.43% to -11.00%**; paired
standardized effect **dz = 0.764**). It also changed:

- maximum raw hazard by -0.060 (95% CI -0.100 to -0.027);
- time in raw high-risk zones by -11.38 percentage points (95% CI -14.26 to
  -8.71).

These outcomes are computed directly from the six raw edge signals, not the
fuzzy objective used to choose the route.

### Proposed fuzzy model versus objective linear baseline

On the optimization-scale fuzzy exposure, the proposed method was lower on 11
pairs, higher on 5 and identical on 84; the exact two-sided sign-test p-value
was 0.210. On independent total raw exposure, the mean change versus the linear
baseline was **+0.62%** (95% CI **-0.85% to +2.45%**, dz = -0.072).

Therefore this 100-pair guarded experiment does **not** establish a meaningful
overall superiority over the objective linear baseline. It shows that the
non-compensatory fuzzy design behaves differently on a minority of trips while
performing strongly against the travel-time-only baseline. This honest result
is more defensible than selecting only a metric that favours the proposed
objective.

### Robustness and ablation

- Hiding 20% of deterministic spatial cells changed 49% of paths and increased
  full-data raw exposure by 6.22% (95% CI 3.81% to 8.85%). This quantifies the
  cost of missing location evidence.
- Under independent +/-0.025 raw-input perturbations, 16% of 200 comparisons
  changed path, but mean path Jaccard similarity was 0.961 and the full-data raw
  exposure change was small (-0.71%; 95% CI -1.42% to -0.16%).
- Removing flood changed 62% of routes and increased full raw exposure by
  32.80%; removing landslide changed 16% and increased it by 0.53%.
- Elephant, buffalo, deer and wild-boar ablations changed 0-4% of routes in
  this dataset, which is consistent with sparse/low-variation wildlife evidence
  and must not be hidden.

## What these results support

The evidence supports the limited claim that the implementation is
reproducible, mathematically safety-consistent, operational on a real road
network, and able to find lower-proxy-exposure routes than the baselines for
many sampled trips.

It does not support a claim of 100% accuracy, guaranteed road safety, proven
causal benefit or population-wide generalization.

## Threats to validity

- The 100 OD pairs are fixed-seed network samples, not a population survey.
- The combined grid has 228 points at about 2.5 km spacing.
- The road graph extends beyond the core grid for some locations.
- Wildlife evidence is sparse and imbalanced across species.
- Flood and landslide values in the base graph are static proxies until live
  detector updates are posted.
- CRITIC weights can change when the input dataset changes.
- Most fuzzy-versus-linear pairs tie, and their independent difference is not
  statistically distinguishable from zero in this sample.
- Spatial holdout degraded results, showing sensitivity to missing hazard
  coverage.
- Field observations of actual safe/unsafe journeys are not yet available.

## Panel answer: why this is research

The contribution is not the map screen. It is the design and objective
evaluation of a specific multi-criteria decision model: reproducible CRITIC
weights plus a provably monotonic hierarchical fuzzy aggregation inside
risk-aware A-star routing, compared against two simpler baselines on the same
real infrastructure.

## Panel answer: is it AI or ML?

The teammate detectors may use machine learning. This component is
multi-criteria decision intelligence using objective weighting, fuzzy logic
and graph search; it does not learn labels from a training set.

## Panel answer: is it 100% accurate?

No responsible route-risk study can promise that. This implementation provides
internal validity, reproducible comparisons, explicit uncertainty and a
detour guardrail. External field validation is the next research stage.

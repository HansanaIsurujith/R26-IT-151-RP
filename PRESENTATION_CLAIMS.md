# Final Presentation Terminology and Claim Boundary

Use this wording consistently in the report, slides, poster and viva.

## Implemented method

**Objective-weighted monotonic hierarchical fuzzy aggregation with risk-aware
A-star routing.**

- CRITIC derives objective information weights from criterion contrast and
  non-redundancy in the 228-row hazard dataset.
- The weighted product-complement aggregation is bounded and monotonic: raising
  any hazard cannot lower the calculated proxy risk.
- A-star minimizes travel time multiplied by the risk penalty.
- A per-route guardrail limits travel-time overhead to 30% versus Fastest.

## Do not use these old explanations

- Do not say that human judges or questionnaires determine the weights.
- Do not describe the final method as AHP.
- Do not describe it as a traditional Mamdani rule-base.
- Do not say that CRITIC identifies which hazard is most dangerous to humans.
- Do not call historical/base hazard values real-time observations.

CRITIC weights describe the information structure of this dataset, not human
severity. Live data exists only after a detector posts a normalized event to
`/hazards/update`.

## Correct result claim

“On 100 fixed-seed connected OD pairs from the Gampaha network, the guarded
model produced reproducible route decisions and was evaluated using raw
per-hazard exposures, maximum raw segment hazard, high-risk-zone time,
travel-time overhead, spatial holdout, perturbation stability and ablation.
Results apply to the supplied proxy data and tested network.”

Use the exact numeric confidence intervals from
`backend/Route-Optimization/results/objective_route_benchmark_summary.json`.

## Safety claim

“The model provides lower-proxy-exposure route decision support, subject to the
coverage, timeliness and quality of the hazard data.”

Never claim:

- 100% safe;
- 100% accurate;
- guaranteed passability;
- validated reduction in real accidents;
- completed field validation;
- deployed teammate integration unless the actual teammate service produced
  the recorded update.

If Risk-Aware and Fastest select the same road path, say:

“The methods selected one identical path because no distinct lower-exposure
alternative was chosen within the 30% detour guardrail.”

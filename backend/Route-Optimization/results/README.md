# Research results

This directory contains reproducible Option B outputs generated from the
current hazard dataset and road network.

- Run python scripts/validate_objective_model.py for mathematical-property
  tests and bootstrap stability of the CRITIC weights.
- Run `python scripts/run_objective_experiment.py --pairs 100 --lambdas 8` for
  guarded paired comparisons, independent raw outcomes, confidence intervals,
  spatial holdout, perturbation stability and hazard ablation.
- Run `python scripts/demonstrate_live_hazard_update.py` for reproducible
  before/update/after API evidence. The output explicitly labels its detector
  event as simulated.

These outputs are internal validation and comparative performance evidence.
They are not labelled human ground truth and do not prove 100% real-world
accuracy or guarantee that a route is safe.

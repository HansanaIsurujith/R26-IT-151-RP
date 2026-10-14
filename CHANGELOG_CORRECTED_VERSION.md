# Corrected Version — What Changed

## Mobile and Expo

- Expo aligned to SDK 54.0.37 and `babel-preset-expo` constrained to `~54.0.10`.
- Minimum Node version set to 20.19.4.
- Unused unmaintained geolocation dependency removed; Expo Location retained.
- Hard-coded Google Maps credential removed and replaced with environment config.
- Coordinate text entry replaced by Gampaha town/road-name search.
- Map taps and current location receive a nearby human-readable name.
- Added clearer empty, loading, outside-coverage and same-path states.
- Risk-Aware/Fastest equality is explicitly shown as one shared road path.
- Open routes automatically recalculate after a new hazard version is detected.

## Backend and integration

- Added `/locations/search` and `/locations/reverse` endpoints.
- Live hazard updates persist in SQLite and replay after restart.
- Added an automatic bridge from the included Flood/Landslide API to routing.
- Added reproducible before/update/after live-routing evidence.
- Response models now state whether each method selected the Fastest path.

## Research validation

- Increased the saved benchmark from 20 to 100 connected OD pairs.
- Applied the same 30% per-route detour guardrail used by the production API.
- Added raw per-hazard exposure, maximum raw hazard and high-risk-zone time.
- Added 95% paired bootstrap intervals and standardized paired effects.
- Added 20% held-out spatial-cell evaluation.
- Added small-input route-stability testing.
- Added six leave-one-hazard-out ablations.
- Reported the inconclusive fuzzy-versus-linear result without exaggeration.

## Terminology and claims

- Final name: objective-weighted monotonic hierarchical fuzzy aggregation.
- CRITIC is described as information weighting, not human danger severity.
- Old questionnaire/AHP and Mamdani-rule explanations are excluded from the
  final package.
- All documentation rejects perfect-accuracy, guaranteed-safety and completed
  field-validation claims.

## Verification completed

- 27 backend tests passed.
- Python compilation passed.
- TypeScript validation passed.
- Expo Doctor passed 18/18 checks.
- Android production export passed (848 bundled modules).
- Real-network live update changed version, route exposure and Risk-Aware path.

Physical-phone interaction remains a manual acceptance step; use
`PHONE_ACCEPTANCE_TEST.md` and record the API terminal together with the phone.

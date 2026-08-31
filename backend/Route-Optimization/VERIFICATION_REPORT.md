# Verification Report

Generated for the corrected Option B package on 2026-08-30.

## Research model

- CRITIC weights calculated from 228 complete rows.
- Weight sum: 1.000000.
- Dataset SHA-256 recorded by the API and result files.
- All-zero risk boundary: 0.0.
- All-one risk boundary: 1.0.
- Random monotonicity audit: 100,000 checks, zero violations.
- Hierarchical/direct equivalence: 10,000 checks passed.
- CRITIC bootstrap stability: 1,000 resamples completed.

## Real road graph

- Nodes loaded: 73,603.
- Edges loaded: 165,094.
- Objective risk caches prepared: 165,094.
- Fastest, objective-linear and objective-fuzzy A-star routes all returned
  valid paths on the real graph.
- Full API response validation passed on the real graph.
- Detour-guardrail adjustment passed.
- Spatial live update passed and affected 2,709 real edge records in the
  isolated reproducible demonstration process.

## Paired experiment

- 100 fixed-seed connected OD pairs and 300 guarded method-trip records.
- Every route respected the production 30% per-route detour guardrail;
  observed maximum overhead was 29.34%.
- Raw per-hazard exposure, maximum raw hazard and high-risk-zone time saved.
- 5,000-resample 95% bootstrap intervals and paired effect sizes saved.
- 20% spatial holdout, two perturbation trials and six hazard ablations saved.
- Against Fastest, independent total raw exposure changed by -14.60% (95% CI
  -18.43% to -11.00%).
- The fuzzy-versus-linear independent difference was inconclusive (+0.62%, 95%
  CI -0.85% to +2.45%) and is reported honestly.

## Backend API

Verified functions:

- health and route configuration;
- route optimization;
- all-method comparison;
- response-model validation;
- model evidence;
- route-specific data quality;
- live hazard status and update;
- SQLite replay of live updates after repository restart;
- name-based location search and reverse lookup;
- included Flood/Landslide-to-routing bridge mapping;
- 30% detour guardrail.

Python syntax compilation passed for all current core, API, experiment and
test files.

## Mobile application

- Expo Doctor passed all 18 checks.
- TypeScript no-emit check passed.
- RouteScreen, HomeScreen and App JavaScript parsing passed.
- Expo Android production export passed.
- Android production export completed successfully.
- routeApi supports explicit environment URL and automatic Expo LAN-host
  inference.

## Teammate-component integrity

The following before/after hashes were unchanged:

| Target | SHA-256 |
|---|---|
| Aggregate backend/Flood-Landslide files | a396fd2ddf69f0e263df38ef8a2641bdc0c5649a7e1f175cceae000997f1a9fc |
| MapScreen.js | 97ed6491fbc243ba3cceaad16be720225900eaebc3d02958629ff390050b4b5b |
| disasterApi.ts | a04c5f6cd9eab4d7a68c9d8c0f2dd9f7a42de437a833ceac1e5b012a23cfa81d |
| weatherService.js | f7940004a03faca81b8f878454787c3acaa86a29a2d5ddbc877763da662d81bc |

## Claim boundary

Passing these checks means the software is internally consistent for the
supplied prototype and data. Physical-phone acceptance, teammate deployment
evidence and external field validation remain separate checks. Nothing here
means perfect real-world route accuracy or guaranteed road safety.

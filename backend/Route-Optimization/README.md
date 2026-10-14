# Suraksha Lanka Route Optimization

## Objective-Weighted Monotonic Hierarchical Fuzzy Multi-Hazard Routing

This is the decision-making layer of Suraksha Lanka. Flood/landslide and
wildlife components estimate what hazards are present; this component decides
which road route best balances travel time and simultaneous exposure to:

- flood;
- landslide;
- elephant;
- buffalo;
- deer;
- wild boar.

The component now follows Option B and has no dependency on questionnaires,
pairwise human judgements, simulated judges or claimed human ground truth.

## Research contribution

The proposed model combines three ideas:

1. CRITIC objective weighting derives six information weights from the
   228-row combined hazard grid. The calculation uses each criterion's
   contrast and its non-redundancy with other criteria.
2. A monotonic hierarchical fuzzy operator combines environmental and wildlife
   hazards. Increasing any hazard is mathematically unable to reduce risk.
3. Risk-aware A-star minimizes travel time multiplied by a risk penalty.

The segment cost is:

~~~text
C(e) = travel_time(e) × [1 + lambda × risk(e)]
~~~

The proposed fuzzy aggregation is:

~~~text
risk = 1 - product((1 - hazard_i) ^ normalized_CRITIC_weight_i)
~~~

It is implemented hierarchically for explanation:

- flood + landslide → environmental risk;
- elephant + buffalo → large-mammal risk;
- deer + wild boar → small-mammal risk;
- large + small mammal → wildlife risk;
- environmental + wildlife → overall risk.

Because parent weights equal the sum of child weights, the hierarchy is
mathematically consistent with direct six-hazard aggregation.

### Current reproducible CRITIC weights

| Hazard | Weight |
|---|---:|
| Flood | 0.354526 |
| Landslide | 0.283204 |
| Elephant | 0.048109 |
| Buffalo | 0.095989 |
| Deer | 0.118132 |
| Wild boar | 0.100040 |

These are information weights from the current dataset, not claims that one
hazard is inherently more harmful to people. The API returns the source row
count, formula and SHA-256 dataset checksum for auditability.

## Three research methods

| API method | Purpose |
|---|---|
| shortest_path | Travel-time-only baseline |
| objective_weight | CRITIC-weighted linear baseline |
| objective_fuzzy | Proposed non-compensatory monotonic fuzzy model |

The fuzzy exposure is reported as the optimization-scale metric, but final
evaluation no longer depends on it alone. The benchmark also evaluates all
routes using raw flood, landslide and wildlife exposures, maximum raw hazard,
time inside raw high-risk zones, held-out spatial cells and perturbation
stability. These independent outcomes prevent a circular "model wins on its own
score" conclusion.

The API also enforces a default 30% travel-time detour guardrail. If a requested
safety preference exceeds it, deterministic lambda sensitivity candidates are
evaluated and the lowest-exposure feasible route is returned. The response
reports both requested and effective lambda values and whether adjustment was
needed.

## Verified model properties

The saved results/model_validation.json report currently contains:

- all-zero boundary: 0.0;
- all-one boundary: 1.0;
- 100,000 randomized monotonicity checks: zero violations;
- 10,000 hierarchy-equivalence checks: passed;
- 1,000 bootstrap resamples of CRITIC weights with 95% intervals;
- fixed seed, input checksum and generation metadata.

This establishes reproducibility and internal validity. It does not prove
100% real-world accuracy, guarantee road safety or replace field validation.

## Backend API

The real Gampaha OSM graph contains 73,603 nodes and 165,094 edges. It is
loaded once, and derived edge risks are cached at startup.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /health | Readiness, methods and graph metadata |
| GET | /route/config | Coverage, CRITIC provenance and UI configuration |
| GET | /locations/search | Offline town and bundled OSM road-name search |
| GET | /locations/reverse | Nearby name for a map-selected coordinate |
| POST | /route/optimize | Calculate one route and optional comparison |
| POST | /route/compare | Always calculate all three research methods |
| GET | /hazards/status | Current persistent hazard-data version |
| POST | /hazards/update | Apply a spatial hazard update to nearby roads |
| GET | /research/evidence | Model provenance and monotonicity audit |
| GET | /docs | Interactive Swagger interface |

The route response includes:

- road-snapped origin and destination;
- full route coordinates for the map;
- risk-coloured route sections;
- per-road hazard and risk details;
- time, distance, mean risk, total exposure and maximum segment risk;
- comparison with both baselines;
- route-specific evidence-coverage level and limitations;
- model name, objective weights and dataset checksum.

### Start on Windows

Open Command Prompt in backend\Route-Optimization:

~~~bat
py -3.14 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python run_api.py
~~~

Wait for Application startup complete. Open this address on the PC:

~~~text
http://127.0.0.1:8001/health
~~~

Do not open 0.0.0.0 in a browser. It is the server bind address, not a client
address.

### Example route request

~~~json
{
  "origin": {
    "latitude": 7.0917,
    "longitude": 79.9942,
    "label": "Gampaha"
  },
  "destination": {
    "latitude": 7.1447,
    "longitude": 80.0960,
    "label": "Nittambuwa"
  },
  "method": "objective_fuzzy",
  "risk_aversion": 8,
  "include_comparison": true
}
~~~

### Live detector integration

Other components can send normalized values in [0, 1] without changing their
own code. Example:

~~~json
POST /hazards/update
{
  "coordinate": {
    "latitude": 7.0917,
    "longitude": 79.9942,
    "label": "Detector cell"
  },
  "radius_km": 1.5,
  "hazards": {
    "flood": 0.91,
    "landslide": 0.22
  },
  "source": "flood-landslide-api",
  "observed_at": "2026-08-28T12:00:00Z"
}
~~~

The update invalidates only affected edge caches, increments hazard_version and
is written to local SQLite storage. Stored updates are replayed when the API
restarts. Production deployment still requires authentication and a managed
database, but the final prototype no longer silently loses updates on restart.

## Mobile application

The routing screen uses the same react-native-maps Google map already used by
the main application. The modern map-first screen provides:

- name-based town/road search, reverse-named map taps, GPS origin and swapping;
- Risk-Aware, Objective Baseline and Fastest modes;
- Flexible, Balanced and Safety-first preferences;
- risk-coloured route geometry and endpoint markers;
- route time, distance, risk, exposure reduction and severe sections;
- full analysis sheet with three-method comparison;
- six-hazard bars and objective weights;
- highest-risk road-section list;
- route-specific evidence-quality warnings;
- model provenance, live hazard version and share action.

Set the PC address in suraksha-lanka\.env:

~~~env
EXPO_PUBLIC_ROUTE_API_URL=http://192.168.8.101:8001
EXPO_PUBLIC_GOOGLE_MAPS_API_KEY=YOUR_RESTRICTED_ANDROID_MAPS_KEY
~~~

The route client can also infer the Expo LAN host automatically. The explicit
.env value is recommended for a predictable demonstration and always takes
priority.

Then start Expo from suraksha-lanka:

~~~bat
set REACT_NATIVE_PACKAGER_HOSTNAME=192.168.8.101
npx expo start --lan -c
~~~

The PC and phone must be on the same Wi-Fi network. Keep the API Command Prompt
open while using the routing screen.

## Tests and experiments

Run the automated suite:

~~~bat
pytest -q
~~~

Regenerate mathematical validation:

~~~bat
python scripts\validate_objective_model.py
~~~

Run paired real-network experiments:

~~~bat
python scripts\run_objective_experiment.py --pairs 100 --lambdas 8
~~~

The final benchmark uses 100 fixed-seed connected OD pairs. It reports raw
per-hazard exposure, maximum raw hazard, high-risk-zone time, travel overhead,
95% bootstrap confidence intervals and paired standardized effects. It also
runs a 20% spatial holdout, small-input perturbation stability checks and six
leave-one-hazard-out ablations. Use `--lambdas 2,4,8,12` when a full lambda
sensitivity run is required.

Generate live detector-flow evidence:

~~~bat
python scripts\demonstrate_live_hazard_update.py
~~~

The output clearly identifies its payload as a simulated detector event; it
proves the integration contract and state/routing reaction, not a deployed
teammate service.

Connect the included teammate Flood/Landslide API on port 8000:

~~~bat
python scripts\sync_flood_landslide_service.py --once
~~~

Without `--once`, the bridge polls continuously (five-minute default), merges
flood and landslide probabilities by grid location and forwards the highest-risk
locations to the persistent routing update endpoint.

## Important limitations

- The base hazard grid has only 228 points at about 2.5 km spacing.
- Parts of the OSM graph extend beyond the core hazard grid; each response
  reports route-specific coverage instead of hiding this issue.
- Wildlife evidence is sparse for some species and locations.
- Static graph values are proxy estimates until detector components post live
  updates.
- CRITIC measures information contrast and non-redundancy, not human severity.
- Lambda is a user preference and must be reported with sensitivity results.
- CORS and hazard updates are open for the local-network prototype; production
  deployment requires authentication, source authorization and restricted CORS.
- The application is research decision support, not emergency-service advice.

## Terminology boundary

The final deliverable uses **objective-weighted monotonic hierarchical fuzzy
aggregation**. It is not presented as a traditional Mamdani rule-based fuzzy
inference system. CRITIC weights describe information contrast and
non-redundancy in the dataset; they do not rank human danger severity. Earlier
questionnaire-based weighting artifacts are excluded from the final ZIP so
they cannot be confused with the implemented method.

## Component isolation

The routing service runs independently on port 8001. The Flood/Landslide
backend, its disaster API service, its MapScreen and the wildlife component
remain separate. Integration additions are limited to the new route service,
route API client, route screen and navigation entry.

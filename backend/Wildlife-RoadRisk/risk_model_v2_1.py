import math
from datetime import datetime
import openpyxl


DATA_FILE = "wildlife_road_master_step1.xlsx"

SPECIES = [
    "Elephant",
    "Buffalo",
    "Wild Boar",
    "Spotted Deer"
]
SPECIES_ICONS = {
    "Elephant": "elephant",
    "Buffalo": "buffalo",
    "Wild Boar": "wild_boar",
    "Spotted Deer": "spotted_deer"
}



# =====================================================
# TEMPORAL ACTIVITY TABLE
# =====================================================

TEMPORAL_ACTIVITY = {

    "Elephant": {
        "Morning": 1.0,
        "Day": 0.8,
        "Evening": 1.3,
        "Night": 1.3
    },

    "Buffalo": {
        "Morning": 1.0,
        "Day": 1.0,
        "Evening": 1.0,
        "Night": 1.0
    },

    "Wild Boar": {
        "Morning": 0.8,
        "Day": 0.7,
        "Evening": 1.3,
        "Night": 1.6
    },

    "Spotted Deer": {
        "Morning": 1.0,
        "Day": 0.8,
        "Evening": 1.3,
        "Night": 1.0
    }

}

# V2 neighbourhood search.
# We start with 10 km, but this is a research parameter that
# will later be tested rather than assumed to be optimal.
SEARCH_RADII_KM = [5.0, 10.0, 15.0, 20.0]

def get_time_period(current_time):
    """
    Convert the current time into one of four periods:
    Morning, Day, Evening or Night.
    """

    hour = current_time.hour

    if 5 <= hour < 9:
        return "Morning"

    elif 9 <= hour < 17:
        return "Day"

    elif 17 <= hour < 20:
        return "Evening"

    else:
        return "Night"

def get_temporal_multiplier(species, current_time):
    """
    Return the activity multiplier for a species
    based on the current time.
    """

    period = get_time_period(current_time)

    return TEMPORAL_ACTIVITY[species][period]


def haversine_km(lat1, lon1, lat2, lon2):
    """
    Calculate geographic distance between two GPS coordinates.
    """

    earth_radius = 6371.0088

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    delta_lat = lat2 - lat1
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    return 2 * earth_radius * math.asin(math.sqrt(a))


def gps_quality_weight(uncertainty):
    """
    Higher-quality GPS observations receive greater influence.
    """

    if uncertainty is None:
        return 0.50

    if uncertainty <= 100:
        return 1.00

    if uncertainty <= 500:
        return 0.85

    if uncertainty <= 1000:
        return 0.70

    if uncertainty <= 5000:
        return 0.45

    return 0.20


def road_relevance_weight(distance_to_road):
    """
    Wildlife observations closer to mapped roads are more
    relevant to a driver encounter-risk model.
    """

    if distance_to_road <= 100:
        return 1.00

    if distance_to_road <= 500:
        return 0.90

    if distance_to_road <= 1000:
        return 0.75

    if distance_to_road <= 5000:
        return 0.45

    return 0.20


def distance_weight(distance_km):
    """
    Nearby observations contribute more evidence.

    Exponential distance decay avoids a hard grid boundary.
    """

    return math.exp(-distance_km / 3.0)


def load_observations():
    """
    Load the 4,130 individual wildlife observations.
    """

    workbook = openpyxl.load_workbook(
        DATA_FILE,
        read_only=True,
        data_only=True
    )

    sheet = workbook.active

    rows = sheet.iter_rows(values_only=True)

    headers = list(next(rows))

    column = {
        name: index
        for index, name in enumerate(headers)
    }

    observations = []

    for row in rows:

        try:
            species = row[column["Species"]]
            latitude = float(row[column["Latitude"]])
            longitude = float(row[column["Longitude"]])

            uncertainty = row[
                column["Coordinate Uncertainty (m)"]
            ]

            road_distance = row[
                column["Distance to Road (m)"]
            ]

            if uncertainty is not None:
                uncertainty = float(uncertainty)

            road_distance = float(road_distance)

        except (ValueError, TypeError, KeyError):
            continue

        observations.append({
            "species": species,
            "latitude": latitude,
            "longitude": longitude,
            "uncertainty": uncertainty,
            "road_distance": road_distance
        })

    workbook.close()

    return observations


def calculate_species_evidence(
    driver_lat,
    driver_lon,
    observations,
    current_time,
    search_radius_km
):

    evidence = {
    species: {
        "weighted_evidence": 0.0,
        "observations": 0,
        "nearest_distance_km": None,
        "gps_quality_scores": []
    }
    for species in SPECIES
}
    for observation in observations:

        species = observation["species"]

        if species not in evidence:
            continue

        distance = haversine_km(
            driver_lat,
            driver_lon,
            observation["latitude"],
            observation["longitude"]
        )

        if distance > search_radius_km:
            continue

        gps_weight = gps_quality_weight(
            observation["uncertainty"]
        )
        evidence[species]["gps_quality_scores"].append(
            gps_weight
        )

        road_weight = road_relevance_weight(
            observation["road_distance"]
        )

        proximity_weight = distance_weight(distance)

        temporal_weight = get_temporal_multiplier(
            species,
            current_time
        )

        observation_evidence = (
            gps_weight
            * road_weight
            * proximity_weight
            * temporal_weight
        )

        evidence[species]["weighted_evidence"] += (
            observation_evidence
        )

        evidence[species]["observations"] += 1

        nearest = evidence[species][
            "nearest_distance_km"
        ]

        if nearest is None or distance < nearest:
            evidence[species][
                "nearest_distance_km"
            ] = distance

    return evidence

def calculate_species_risk_scores(evidence):
    """
    Convert each species' weighted evidence into a relative
    0-100 score within the current evaluation location.

    The strongest species receives 100 and the other species
    are scored relative to it. These are relative evidence scores,
    not probabilities of road crossing.
    """

    max_evidence = max(
        result["weighted_evidence"]
        for result in evidence.values()
    )

    species_scores = {}

    if max_evidence <= 0:
        for species in evidence:
            species_scores[species] = 0.0
        return species_scores

    for species, result in evidence.items():

        weighted_evidence = result["weighted_evidence"]

        score = (
            weighted_evidence / max_evidence
        ) * 100.0

        species_scores[species] = score

    return species_scores

def get_risk_color(risk_level):
    """
    Convert a wildlife risk level into a UI colour.

    These colours are for visualisation only.
    """

    if risk_level == "LOW":
        return "GREEN"

    elif risk_level == "MODERATE":
        return "YELLOW"

    elif risk_level == "HIGH":
        return "ORANGE"

    elif risk_level == "VERY HIGH":
        return "RED"

    return "GREY"

def classify_species_risk(
    species_score,
    weighted_evidence
):
    """
    Classify wildlife evidence into a risk level.

    The classification is based on the relative species score only.
    The numerical score is preserved exactly; only the label and
    colour mapping are derived from the required score ranges.
    """

    if species_score < 25.0:
        return "LOW"

    if species_score < 50.0:
        return "MODERATE"

    if species_score < 75.0:
        return "HIGH"

    return "VERY HIGH"

def build_species_results(
    evidence,
    species_risk_scores,
    current_time=None
):
    """
    Build structured wildlife results for each species.

    These results will later be used by the FastAPI backend
    and React Native frontend.
    """

    species_results = []

    for species in SPECIES:

        species_evidence = evidence[species]
        weighted_evidence = species_evidence["weighted_evidence"]
        score = species_risk_scores[species]

        risk_level = classify_species_risk(
            score,
            weighted_evidence
        )

        risk_color = get_risk_color(
            risk_level
        )

        icon_name = SPECIES_ICONS[species]

        nearest_distance = species_evidence["nearest_distance_km"]

        if current_time is not None:
            temporal_multiplier = get_temporal_multiplier(
                species,
                current_time
            )
        else:
            temporal_multiplier = None

        species_results.append({
            "species": species,
            "score": round(score, 1),
            "risk_level": risk_level,
            "colour": risk_color,
            "icon": icon_name,
            "observations": species_evidence["observations"],
            "weighted_evidence": round(weighted_evidence, 3),
            "nearest_distance_km": None if nearest_distance is None else round(nearest_distance, 3),
            "temporal_multiplier": temporal_multiplier
        })

    return species_results


def calculate_confidence(
    evidence,
    search_radius_km
):
    """
    Estimate confidence in the available local wildlife evidence.

    Confidence considers:
    1. Number of observations
    2. GPS quality
    3. Distance-weighted proximity
    4. Overall evidence strength

    This is a data-confidence measure, not a probability
    that an animal will cross the road.
    """

    total_observations = sum(
        result["observations"]
        for result in evidence.values()
    )

    if total_observations == 0:
        return 0.0

    # -------------------------------------------------
    # 1. Observation support
    # -------------------------------------------------

    observation_score = min(
        total_observations / 10.0,
        1.0
    )

    # -------------------------------------------------
    # 2. GPS quality
    # -------------------------------------------------

    gps_scores = []

    for result in evidence.values():

        gps_scores.extend(
            result["gps_quality_scores"]
        )

    if gps_scores:

        gps_quality_score = (
            sum(gps_scores) / len(gps_scores)
        )

    else:

        gps_quality_score = 0.0

    # -------------------------------------------------
    # 3. Distance-weighted proximity
    # -------------------------------------------------

    proximity_scores = []

    for result in evidence.values():

        nearest = result["nearest_distance_km"]

        if nearest is not None:

            proximity_score = math.exp(
                -nearest / 3.0
            )

            proximity_scores.append(
                proximity_score
            )

    if proximity_scores:

        proximity_score = max(
            proximity_scores
        )

    else:

        proximity_score = 0.0

    # -------------------------------------------------
    # 4. Evidence strength
    # -------------------------------------------------

    total_weighted_evidence = sum(
        result["weighted_evidence"]
        for result in evidence.values()
    )

    evidence_score = min(
        total_weighted_evidence / 3.0,
        1.0
    )

    # -------------------------------------------------
    # Combine components
    # -------------------------------------------------

    confidence = (
        observation_score * 0.30
        + gps_quality_score * 0.25
        + proximity_score * 0.25
        + evidence_score * 0.20
    )

    return confidence * 100.0

def calculate_risk_score(evidence):
    """
    Convert the strongest species evidence into a
    relative 0-100 encounter-risk evidence score.

    This is NOT the probability of an animal crossing
    the road.
    """

    strongest_evidence = max(
        result["weighted_evidence"]
        for result in evidence.values()
    )

    # Provisional normalization ceiling.
    # This parameter will later be tested through
    # sensitivity analysis.
    NORMALIZATION_CEILING = 1.0

    risk_score = (
        strongest_evidence
        / NORMALIZATION_CEILING
    ) * 100.0

    risk_score = min(
        risk_score,
        100.0
    )

    return risk_score



def print_result(
    latitude,
    longitude,
    evidence,
    current_time,
    confidence,
    risk_score,
    search_radius_km,
    species_risk_scores
):


    print()
    print("=" * 55)
    print("ROADRISK - WILDLIFE ENCOUNTER MODEL V2")
    print("=" * 55)

    print(f"Driver GPS: {latitude}, {longitude}")
    print(f"Search radius: {search_radius_km} km")
    print(
    f"Evaluation time: "
    f"{current_time.strftime('%Y-%m-%d %H:%M:%S')}"
)

    print()
    print("SPECIES RISK LEVELS")
    print("-" * 55)

    for species in SPECIES:

        species_score = species_risk_scores[species]
        icon_name = SPECIES_ICONS[species]

        weighted_evidence = evidence[species][
            "weighted_evidence"
        ]

        risk_level = classify_species_risk(
            species_score,
            weighted_evidence
        )
        risk_color = get_risk_color(
    risk_level
)

        print(
            f"{species}: "
            f"{species_score:.1f}/100 "
            f"| Risk Level: {risk_level} "
            f"| Colour: {risk_color}"
            f"| Icon: {icon_name}"
        )

    for species in SPECIES:

        result = evidence[species]

        nearest = result["nearest_distance_km"]
        temporal_period = get_time_period(current_time)
        temporal_multiplier = get_temporal_multiplier(
            species,
            current_time
        )

        if nearest is None:
            nearest_text = "None within radius"
        else:
            nearest_text = f"{nearest:.2f} km"

        print()
        print(species)
        print(
            f"  Observations: "
            f"{result['observations']}"
        )
        print(
            f"  Weighted evidence: "
            f"{result['weighted_evidence']:.3f}"
        )
        print(
            f"  Time period: {temporal_period}"
        )
        print(
            f"  Temporal multiplier: "
            f"{temporal_multiplier:.2f}"
        )
        print(
            f"  Nearest observation: "
            f"{nearest_text}"
        )

    dominant_species = max(
        SPECIES,
        key=lambda species:
        evidence[species]["weighted_evidence"]
    )

    dominant_evidence = evidence[
        dominant_species
    ]["weighted_evidence"]

    print()
    print("=" * 55)
    print(
    f"ENCOUNTER RISK SCORE: "
    f"{risk_score:.1f}/100"
)
    print(
    f"DATA CONFIDENCE: {confidence:.1f}/100"
)

    if dominant_evidence == 0:

        print(
            "RESULT: INSUFFICIENT LOCAL "
            "WILDLIFE EVIDENCE"
        )

    else:

        print(
            f"STRONGEST LOCAL EVIDENCE: "
            f"{dominant_species}"
        )

    print("=" * 55)

    print()
    print("=" * 55)
    print("WILDLIFE RESULT SUMMARY")
    print("=" * 55)



def evaluate_live_location(
    driver_latitude,
    driver_longitude,
    current_time,
    observations,
    search_radius_km=10.0
):
    """
    Evaluate local wildlife encounter evidence for one live location.
    Returns a JSON-friendly dictionary for API use.
    """

    evidence = calculate_species_evidence(
        driver_latitude,
        driver_longitude,
        observations,
        current_time,
        search_radius_km
    )

    confidence = calculate_confidence(
        evidence,
        search_radius_km
    )

    risk_score = calculate_risk_score(
        evidence
    )

    species_risk_scores = calculate_species_risk_scores(
        evidence
    )

    species_results = build_species_results(
        evidence,
        species_risk_scores,
        current_time=current_time
    )

    return {
        "latitude": driver_latitude,
        "longitude": driver_longitude,
        "evaluation_time": current_time.isoformat(),
        "search_radius_km": search_radius_km,
        "encounter_risk_score": round(risk_score, 1),
        "data_confidence": round(confidence, 1),
        "species": species_results
    }


def main():

    print("Loading wildlife observations...")

    observations = load_observations()

    test_latitude = 8.0
    test_longitude = 80.8
    test_time = datetime.now()

    live_result = evaluate_live_location(
        test_latitude,
        test_longitude,
        test_time,
        observations,
        search_radius_km=10.0
    )

    print()
    print("=" * 60)
    print("LIVE LOCATION TEST")
    print("=" * 60)

    print(live_result)

    test_radius = 10.0

    print()
    print("=" * 60)
    print("TIME SENSITIVITY TEST")
    print("=" * 60)

    sensitivity_times = [
        datetime(2026, 8, 23, 6, 0, 0),
        datetime(2026, 8, 23, 12, 0, 0),
        datetime(2026, 8, 23, 18, 0, 0),
        datetime(2026, 8, 23, 22, 0, 0),
        datetime(2026, 8, 24, 2, 0, 0)
    ]

    for test_time in sensitivity_times:

        result = evaluate_live_location(
            test_latitude,
            test_longitude,
            test_time,
            observations,
            search_radius_km=test_radius
        )

        print()
        print("-" * 60)
        print(
            f"Time: {test_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(
            f"Location: {test_latitude}, {test_longitude}"
        )
        print(
            f"Encounter Risk: "
            f"{result['encounter_risk_score']:.1f}/100"
        )
        print(
            f"Data Confidence: "
            f"{result['data_confidence']:.1f}/100"
        )

        print("Species:")

        for animal in result["species"]:

            print(
                f"  {animal['species']}: "
                f"{animal['score']:.1f}/100 | "
                f"{animal['risk_level']} | "
                f"{animal['colour']} | "
                f"Temporal multiplier: "
                f"{animal['temporal_multiplier']:.2f}"
            )

    print()
    print("=" * 60)
    print("GPS LOCATION SENSITIVITY TEST")
    print("=" * 60)

    location_tests = [
        {
            "name": "Location 1",
            "latitude": 6.851236,
            "longitude": 80.009918
        },
        {
            "name": "Location 2",
            "latitude": 6.9,
            "longitude": 80.1
        },
        {
            "name": "Location 3",
            "latitude": 7.0,
            "longitude": 80.5
        },
        {
            "name": "Location 4",
            "latitude": 7.5,
            "longitude": 80.7
        },
        {
            "name": "Location 5",
            "latitude": 8.0,
            "longitude": 80.8
        }
    ]

    evaluation_time = datetime(2026, 8, 23, 22, 0, 0)

    for location in location_tests:
        result = evaluate_live_location(
            location["latitude"],
            location["longitude"],
            evaluation_time,
            observations,
            search_radius_km=10.0
        )

        strongest_species = None
        if result["species"]:
            strongest_species = max(
                result["species"],
                key=lambda animal: animal["score"]
            )["species"]

        print()
        print("-" * 60)
        print(f"Location: {location['name']}")
        print(f"Latitude: {location['latitude']}")
        print(f"Longitude: {location['longitude']}")
        print(
            f"Encounter Risk: "
            f"{result['encounter_risk_score']:.1f}/100"
        )
        print(
            f"Data Confidence: "
            f"{result['data_confidence']:.1f}/100"
        )
        print(
            f"Strongest species: "
            f"{strongest_species if strongest_species is not None else 'None'}"
        )

        for animal in result["species"]:
            nearest = animal.get("nearest_distance_km")
            print(
                f"  {animal['species']}: "
                f"{animal['score']:.1f}/100 | "
                f"{animal['risk_level']} | "
                f"{animal['colour']} | "
                f"Nearest distance: "
                f"{nearest if nearest is not None else 'None'}"
            )

    print(
        f"Loaded {len(observations)} "
        f"wildlife observations."
    )

    # -------------------------------------------------
    # VALIDATION CASE #1
    #
    # This location is NOT added to the training data.
    # It remains independent validation information.
    # -------------------------------------------------

    validation_locations = [
        {
            "name": "Location 1",
            "latitude": 6.851236,
            "longitude": 80.009918
        },
        {
            "name": "Location 2",
            "latitude": 6.900000,
            "longitude": 80.100000
        },
        {
            "name": "Location 3",
            "latitude": 7.000000,
            "longitude": 80.500000
        },
        {
            "name": "Location 4",
            "latitude": 7.500000,
            "longitude": 80.700000
        },
        {
            "name": "Location 5",
            "latitude": 8.000000,
            "longitude": 80.800000
        }
    ]

    current_time = datetime(2026, 8, 23, 22, 0, 0)

    for location in validation_locations:

        location_name = location["name"]
        driver_latitude = location["latitude"]
        driver_longitude = location["longitude"]

        print()
        print("#" * 60)
        print(f"VALIDATION LOCATION: {location_name}")
        print(f"GPS: {driver_latitude}, {driver_longitude}")
        print("#" * 60)

        for search_radius_km in SEARCH_RADII_KM:

            print()
            print("=" * 60)
            print(f"TESTING SEARCH RADIUS: {search_radius_km} km")
            print("=" * 60)

            evidence = calculate_species_evidence(
                driver_latitude,
                driver_longitude,
                observations,
                current_time,
                search_radius_km
            )

            confidence = calculate_confidence(
                evidence,
                search_radius_km
            )

            risk_score = calculate_risk_score(
                evidence
            )

            species_risk_scores = calculate_species_risk_scores(
                evidence
            )
            species_results = build_species_results(
                evidence,
                species_risk_scores,
                current_time=current_time
            )

            print()
            print("STRUCTURED SPECIES RESULTS")
            print("-" * 55)

            for animal in species_results:
                print(animal)

            print_result(
                driver_latitude,
                driver_longitude,
                evidence,
                current_time,
                confidence,
                risk_score,
                search_radius_km,
                species_risk_scores,
            )


if __name__ == "__main__":
    main()
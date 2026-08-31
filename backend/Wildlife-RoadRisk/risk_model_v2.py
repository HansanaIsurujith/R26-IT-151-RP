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

# V2 neighbourhood search.
# We start with 10 km, but this is a research parameter that
# will later be tested rather than assumed to be optimal.
SEARCH_RADIUS_KM = 10.0


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
    observations
):

    evidence = {
        species: {
            "weighted_evidence": 0.0,
            "observations": 0,
            "nearest_distance_km": None
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

        if distance > SEARCH_RADIUS_KM:
            continue

        gps_weight = gps_quality_weight(
            observation["uncertainty"]
        )

        road_weight = road_relevance_weight(
            observation["road_distance"]
        )

        proximity_weight = distance_weight(distance)

        observation_evidence = (
            gps_weight
            * road_weight
            * proximity_weight
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


def print_result(
    latitude,
    longitude,
    evidence
):

    print()
    print("=" * 55)
    print("ROADRISK - WILDLIFE ENCOUNTER MODEL V2")
    print("=" * 55)

    print(f"Driver GPS: {latitude}, {longitude}")
    print(f"Search radius: {SEARCH_RADIUS_KM} km")

    print()
    print("NEARBY WILDLIFE EVIDENCE")
    print("-" * 55)

    for species in SPECIES:

        result = evidence[species]

        nearest = result["nearest_distance_km"]

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
    print(
        "NOTE: Evidence values are not "
        "probabilities of road crossing."
    )


def main():

    print("Loading wildlife observations...")

    observations = load_observations()

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

    driver_latitude = 6.851236
    driver_longitude = 80.009918

    evidence = calculate_species_evidence(
        driver_latitude,
        driver_longitude,
        observations
    )

    print_result(
        driver_latitude,
        driver_longitude,
        evidence
    )


if __name__ == "__main__":
    main()
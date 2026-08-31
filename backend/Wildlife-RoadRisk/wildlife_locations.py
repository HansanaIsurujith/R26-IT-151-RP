"""Wildlife evidence locations for map and route integrations."""

from collections import defaultdict
from datetime import datetime

from risk_model_v2_1 import (
    SPECIES,
    SPECIES_ICONS,
    classify_species_risk,
    distance_weight,
    get_risk_color,
    get_temporal_multiplier,
    gps_quality_weight,
    haversine_km,
    road_relevance_weight,
)


GROUPING_TOLERANCE_M = 200.0
GROUPING_TOLERANCE_KM = GROUPING_TOLERANCE_M / 1000.0


def _observation_evidence(observation, distance_km, current_time):
    return (
        gps_quality_weight(observation["uncertainty"])
        * road_relevance_weight(observation["road_distance"])
        * distance_weight(distance_km)
        * get_temporal_multiplier(observation["species"], current_time)
    )


def _group_observations(observations):
    """Group observations around a real dataset coordinate, never a synthetic point."""
    groups = []

    for observation in observations:
        matching_group = None
        for group in groups:
            if haversine_km(
                observation["latitude"],
                observation["longitude"],
                group["latitude"],
                group["longitude"],
            ) <= GROUPING_TOLERANCE_KM:
                matching_group = group
                break

        if matching_group is None:
            groups.append(
                {
                    "latitude": observation["latitude"],
                    "longitude": observation["longitude"],
                    "observations": [observation],
                }
            )
        else:
            matching_group["observations"].append(observation)

    return groups


def _group_all_observations(observations):
    """Create stable dataset groups without using a driver location."""
    sorted_observations = sorted(
        observations,
        key=lambda observation: (
            observation["latitude"],
            observation["longitude"],
            observation["species"],
        ),
    )
    groups = []

    for observation in sorted_observations:
        matching_group = next(
            (
                group
                for group in groups
                if haversine_km(
                    observation["latitude"],
                    observation["longitude"],
                    group["latitude"],
                    group["longitude"],
                ) <= GROUPING_TOLERANCE_KM
            ),
            None,
        )

        if matching_group is None:
            groups.append(
                {
                    "latitude": observation["latitude"],
                    "longitude": observation["longitude"],
                    "observations": [observation],
                }
            )
        else:
            matching_group["observations"].append(observation)

    groups.sort(key=lambda group: (group["latitude"], group["longitude"]))
    for group_index, group in enumerate(groups, start=1):
        group["location_id"] = f"wildlife-{group_index:04d}"
    return groups


def _nearby_observations(driver_latitude, driver_longitude, observations, search_radius_km):
    nearby_observations = []
    for observation in observations:
        if observation["species"] not in SPECIES:
            continue
        distance_km = haversine_km(
            driver_latitude,
            driver_longitude,
            observation["latitude"],
            observation["longitude"],
        )
        if distance_km <= search_radius_km:
            nearby_observations.append({**observation, "driver_distance_km": distance_km})
    return nearby_observations


def _species_rows(group):
    species_observations = defaultdict(list)
    for observation in group["observations"]:
        species_observations[observation["species"]].append(observation)
    return species_observations


def _build_species_result(species, rows, current_time, maximum_species_evidence):
    evidence = sum(
        _observation_evidence(row, row["driver_distance_km"], current_time)
        for row in rows
    )
    score = (
        evidence / maximum_species_evidence * 100.0
        if maximum_species_evidence > 0
        else 0.0
    )
    risk_level = classify_species_risk(score, evidence)
    return {
        "species": species,
        "score": round(score, 1),
        "risk_level": risk_level,
        "risk_colour": get_risk_color(risk_level),
        "observation_count": len(rows),
        "nearest_observation_distance_km": round(
            min(row["driver_distance_km"] for row in rows), 3
        ),
    }, evidence


def _build_location_result(location, current_time, maximum_species_evidence):
    species_observations = _species_rows(location)

    species_results = []
    for species, rows in species_observations.items():
        result, _ = _build_species_result(
            species, rows, current_time, maximum_species_evidence
        )
        species_results.append(result)

    species_results.sort(key=lambda result: result["score"], reverse=True)
    primary = species_results[0]
    representative = location["observations"][0]
    return {
        "location_id": location["location_id"],
        "latitude": representative["latitude"],
        "longitude": representative["longitude"],
        "primary_species": primary["species"],
        "primary_icon": SPECIES_ICONS.get(primary["species"]),
        "primary_score": primary["score"],
        "risk_level": primary["risk_level"],
        "risk_colour": primary["risk_colour"],
        "additional_species_count": max(len(species_results) - 1, 0),
        "species": species_results,
        "observation_count": len(location["observations"]),
        "grouping_tolerance_m": GROUPING_TOLERANCE_M,
        "score_basis": "relative wildlife evidence score",
    }


def build_wildlife_locations(
    driver_latitude,
    driver_longitude,
    current_time,
    observations,
    search_radius_km=10.0,
):
    """Build grouped, historical wildlife evidence locations near a requested point."""
    if search_radius_km <= 0:
        raise ValueError("search_radius_km must be greater than zero.")

    nearby_observations = _nearby_observations(
        driver_latitude,
        driver_longitude,
        observations,
        search_radius_km,
    )

    groups = _group_observations(nearby_observations)
    maximum_species_evidence = 0.0
    group_records = []

    for group_index, group in enumerate(groups, start=1):
        group["location_id"] = f"wildlife-{group_index:04d}"
        group_records.append(group)
        for species_rows in _species_rows(group).values():
            evidence = sum(
                _observation_evidence(row, row["driver_distance_km"], current_time)
                for row in species_rows
            )
            maximum_species_evidence = max(maximum_species_evidence, evidence)

    locations = [
        _build_location_result(group, current_time, maximum_species_evidence)
        for group in group_records
    ]

    locations.sort(key=lambda location: location["primary_score"], reverse=True)
    return {
        "locations": locations,
        "metadata": {
            "search_radius_km": search_radius_km,
            "evaluation_time": current_time.isoformat(),
            "grouping_tolerance_m": GROUPING_TOLERANCE_M,
            "score_interpretation": "Relative evidence score, not crossing probability",
        },
    }


def _map_observation_evidence(observation, group, current_time):
    group_distance_km = haversine_km(
        observation["latitude"],
        observation["longitude"],
        group["latitude"],
        group["longitude"],
    )
    return _observation_evidence(observation, group_distance_km, current_time)


def build_wildlife_map_locations(
    north,
    south,
    east,
    west,
    current_time,
    observations,
):
    """Build historical wildlife evidence locations inside map bounds."""
    if south > north:
        raise ValueError("south must be less than or equal to north.")
    if west > east:
        raise ValueError("west must be less than or equal to east.")

    groups = _group_all_observations(
        [observation for observation in observations if observation["species"] in SPECIES]
    )
    visible_groups = [
        group
        for group in groups
        if south <= group["latitude"] <= north
        and west <= group["longitude"] <= east
    ]

    group_evidence = {}
    maximum_evidence = 0.0
    for group in visible_groups:
        species_rows = _species_rows(group)
        group_evidence[group["location_id"]] = {}
        for species, rows in species_rows.items():
            evidence = sum(
                _map_observation_evidence(row, group, current_time)
                for row in rows
            )
            group_evidence[group["location_id"]][species] = evidence
            maximum_evidence = max(maximum_evidence, evidence)

    locations = []
    for group in visible_groups:
        species_results = []
        for species, evidence in group_evidence[group["location_id"]].items():
            score = evidence / maximum_evidence * 100.0 if maximum_evidence else 0.0
            risk_level = classify_species_risk(score, evidence)
            rows = _species_rows(group)[species]
            species_results.append(
                {
                    "species": species,
                    "icon": SPECIES_ICONS.get(species),
                    "score": round(score, 1),
                    "risk_level": risk_level,
                    "risk_colour": get_risk_color(risk_level),
                    "observation_count": len(rows),
                    "nearest_observation_distance_km": round(
                        min(
                            haversine_km(
                                row["latitude"],
                                row["longitude"],
                                group["latitude"],
                                group["longitude"],
                            )
                            for row in rows
                        ),
                        3,
                    ),
                }
            )

        species_results.sort(key=lambda result: (-result["score"], result["species"]))
        primary = species_results[0]
        locations.append(
            {
                "location_id": group["location_id"],
                "latitude": group["latitude"],
                "longitude": group["longitude"],
                "primary_species": primary["species"],
                "primary_icon": primary["icon"],
                "primary_score": primary["score"],
                "risk_level": primary["risk_level"],
                "risk_colour": primary["risk_colour"],
                "additional_species_count": len(species_results) - 1,
                "species": species_results,
                "observation_count": len(group["observations"]),
                "grouping_tolerance_m": GROUPING_TOLERANCE_M,
                "score_basis": "relative wildlife evidence score",
            }
        )

    return {
        "locations": locations,
        "metadata": {
            "evaluation_time": current_time.isoformat(),
            "grouping_tolerance_m": GROUPING_TOLERANCE_M,
            "score_interpretation": "Relative wildlife evidence score, not crossing probability",
            "viewport": {"north": north, "south": south, "east": east, "west": west},
        },
    }

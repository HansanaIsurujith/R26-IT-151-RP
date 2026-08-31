"""Reproducible, data-derived hazard weights for the Option B model.

The weights are calculated with CRITIC (Criteria Importance Through
Intercriteria Correlation).  CRITIC rewards criteria that contain more
contrast in the observed data and that are less redundant with the other
criteria.  It therefore needs no questionnaires or hand-entered pairwise
judgements.

Important interpretation: these are *information weights*, not claims about
the medical or social severity of a hazard.  The model and API expose that
distinction so results are not presented as human ground truth.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np


HAZARD_COLUMNS = {
    "flood": "flood_probability_proxy",
    "landslide": "landslide_probability_proxy",
    "elephant": "elephant_risk",
    "buffalo": "buffalo_risk",
    "deer": "deer_risk",
    "wildboar": "wildboar_risk",
}

COMPONENT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = COMPONENT_ROOT / "data" / "combined_hazard_grid.csv"


@dataclass(frozen=True)
class ObjectiveWeightResult:
    method: str
    weights: dict[str, float]
    contrast: dict[str, float]
    information: dict[str, float]
    row_count: int
    dataset: str
    dataset_sha256: str
    formula: str

    def as_dict(self) -> dict:
        return {
            "method": self.method,
            "weights": self.weights,
            "contrast": self.contrast,
            "information": self.information,
            "row_count": self.row_count,
            "dataset": self.dataset,
            "dataset_sha256": self.dataset_sha256,
            "formula": self.formula,
        }


def _read_hazard_matrix(path: Path) -> np.ndarray:
    rows: list[list[float]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = set(HAZARD_COLUMNS.values()) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                "Hazard dataset is missing columns: " + ", ".join(sorted(missing))
            )
        for row in reader:
            try:
                values = [float(row[column]) for column in HAZARD_COLUMNS.values()]
            except (TypeError, ValueError, KeyError):
                continue
            if all(np.isfinite(values)):
                rows.append(values)

    if len(rows) < 3:
        raise ValueError("At least three complete hazard observations are required.")
    return np.clip(np.asarray(rows, dtype=float), 0.0, 1.0)


def calculate_critic_weights(path: str | Path = DEFAULT_DATASET) -> ObjectiveWeightResult:
    """Calculate deterministic CRITIC weights from the combined hazard grid.

    For normalized benefit criteria, CRITIC uses

        C_j = sigma_j * sum_k(1 - r_jk)
        w_j = C_j / sum(C)

    where sigma is sample standard deviation and r is Pearson correlation.
    Equal weights are used only if every criterion has zero information.
    """

    dataset_path = Path(path).resolve()
    matrix = _read_hazard_matrix(dataset_path)
    names = list(HAZARD_COLUMNS)

    contrast = np.std(matrix, axis=0, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        correlation = np.corrcoef(matrix, rowvar=False)
    correlation = np.nan_to_num(correlation, nan=0.0, posinf=0.0, neginf=0.0)
    correlation = np.clip(correlation, -1.0, 1.0)
    information = contrast * np.sum(1.0 - correlation, axis=1)

    total_information = float(information.sum())
    if total_information <= 1e-12:
        weights_array = np.full(len(names), 1.0 / len(names), dtype=float)
    else:
        weights_array = information / total_information

    digest = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    return ObjectiveWeightResult(
        method="CRITIC",
        weights={name: float(value) for name, value in zip(names, weights_array)},
        contrast={name: float(value) for name, value in zip(names, contrast)},
        information={name: float(value) for name, value in zip(names, information)},
        row_count=int(matrix.shape[0]),
        dataset=dataset_path.name,
        dataset_sha256=digest,
        formula="C_j = sigma_j * sum_k(1-r_jk); w_j = C_j / sum(C)",
    )


OBJECTIVE_WEIGHT_RESULT = calculate_critic_weights()
OBJECTIVE_WEIGHTS = OBJECTIVE_WEIGHT_RESULT.weights


if __name__ == "__main__":
    result = OBJECTIVE_WEIGHT_RESULT
    print(f"{result.method} objective weights from {result.row_count} observations")
    for hazard, weight in result.weights.items():
        print(f"  {hazard:<10} {weight:.6f}")
    print(f"  sum        {sum(result.weights.values()):.6f}")
    print(f"  sha256     {result.dataset_sha256}")

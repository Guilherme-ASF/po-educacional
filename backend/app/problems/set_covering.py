from __future__ import annotations

from typing import Any

from app.models.problem import Constraint, ObjectiveSense
from app.problems._util import bin_vars, make_model

DEFAULT_INSTANCE: dict[str, Any] = {
    "custos": [120, 80, 150, 90, 110],
    "cobertura": [
        [1, 2, 3, 5],
        [2, 4, 6],
        [1, 3, 5, 7, 8],
        [4, 6, 7],
        [3, 5, 6, 8],
    ],
    "n_zonas": 8,
}


def build_model(data: dict[str, Any]) -> ProblemModel:
    custos = data["custos"]
    cobertura: list[list[int]] = data["cobertura"]
    n_zonas = int(data["n_zonas"])
    n_loc = len(custos)
    names = [f"x{j+1}" for j in range(n_loc)]

    objective = {names[j]: float(custos[j]) for j in range(n_loc)}
    constraints: list[Constraint] = []

    for z in range(1, n_zonas + 1):
        coefs = {
            names[j]: 1.0
            for j in range(n_loc)
            if z in cobertura[j]
        }
        if coefs:
            constraints.append(Constraint(coefs, ">=", 1.0, name=f"zona_{z}"))

    return make_model(
        ObjectiveSense.MIN,
        objective,
        constraints,
        bin_vars(names),
        f"Set covering ({n_zonas} zonas, {n_loc} locais)",
    )

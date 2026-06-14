from __future__ import annotations

from typing import Any

from app.models.problem import Constraint, ObjectiveSense, Variable, VariableType
from app.problems._util import make_model

DEFAULT_INSTANCE: dict[str, Any] = {
    "custos_atend": [
        [3, 8, 6, 9],
        [7, 2, 5, 4],
        [5, 6, 2, 7],
        [9, 3, 8, 2],
        [4, 7, 3, 8],
        [6, 5, 7, 3],
    ],
    "instalacao": [30, 25, 35, 20],
    "max_cidades": 3,
    "orcamento": 120,
}


def build_model(data: dict[str, Any]) -> ProblemModel:
    hij = data["custos_atend"]
    fj = data["instalacao"]
    max_c = int(data["max_cidades"])
    budget = float(data["orcamento"])
    n_reg = len(hij)
    n_cid = len(fj)

    x_names = [f"x_{i}_{j}" for i in range(n_reg) for j in range(n_cid)]
    y_names = [f"y{j+1}" for j in range(n_cid)]
    variables = (
        [Variable(x, VariableType.BINARY) for x in x_names]
        + [Variable(y, VariableType.BINARY) for y in y_names]
    )

    objective: dict[str, float] = {y_names[j]: float(fj[j]) for j in range(n_cid)}
    for i in range(n_reg):
        for j in range(n_cid):
            objective[f"x_{i}_{j}"] = float(hij[i][j])

    constraints: list[Constraint] = []
    for i in range(n_reg):
        constraints.append(
            Constraint(
                {f"x_{i}_{j}": 1.0 for j in range(n_cid)},
                "=",
                1.0,
                name=f"reg_{i}",
            )
        )

    for i in range(n_reg):
        for j in range(n_cid):
            constraints.append(
                Constraint(
                    {f"x_{i}_{j}": 1.0, y_names[j]: -1.0},
                    "<=",
                    0.0,
                    name=f"link_{i}_{j}",
                )
            )

    constraints.append(
        Constraint({y_names[j]: 1.0 for j in range(n_cid)}, "<=", float(max_c), name="max_cid")
    )
    constraints.append(
        Constraint({y_names[j]: float(fj[j]) for j in range(n_cid)}, "<=", budget, name="orc")
    )

    return make_model(
        ObjectiveSense.MIN,
        objective,
        constraints,
        variables,
        f"Facility location ({n_reg} regiões, {n_cid} cidades)",
    )

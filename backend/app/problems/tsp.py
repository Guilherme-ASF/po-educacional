from __future__ import annotations

from typing import Any

from app.models.problem import Constraint, ObjectiveSense, Variable, VariableType
from app.problems._util import make_model

DEFAULT_INSTANCE: dict[str, Any] = {
    "distancias": [
        [0, 10, 15, 20, 18, 25],
        [10, 0, 12, 18, 14, 22],
        [15, 12, 0, 8, 16, 19],
        [20, 18, 8, 0, 11, 14],
        [18, 14, 16, 11, 0, 9],
        [25, 22, 19, 14, 9, 0],
    ],
}


def build_model(data: dict[str, Any]) -> ProblemModel:
    dist: list[list[float]] = data["distancias"]
    n = len(dist)

    x_names: list[str] = []
    for i in range(n):
        for j in range(n):
            if i != j:
                x_names.append(f"x_{i}_{j}")

    u_names = [f"u{i}" for i in range(1, n)]
    variables = (
        [Variable(x, VariableType.BINARY) for x in x_names]
        + [Variable(u, VariableType.CONTINUOUS, lower_bound=0.0) for u in u_names]
    )

    objective = {}
    for i in range(n):
        for j in range(n):
            if i != j:
                objective[f"x_{i}_{j}"] = float(dist[i][j])

    constraints: list[Constraint] = []

    for j in range(n):
        if j == 0:
            continue
        constraints.append(
            Constraint(
                {f"x_{i}_{j}": 1.0 for i in range(n) if i != j},
                "=",
                1.0,
                name=f"entrada_{j}",
            )
        )

    for i in range(n):
        if i == 0:
            continue
        constraints.append(
            Constraint(
                {f"x_{i}_{j}": 1.0 for j in range(n) if j != i},
                "=",
                1.0,
                name=f"saida_{i}",
            )
        )

    # depot flow
    constraints.append(
        Constraint(
            {f"x_0_{j}": 1.0 for j in range(1, n)},
            "=",
            1.0,
            name="sai_depot",
        )
    )
    constraints.append(
        Constraint(
            {f"x_{i}_0": 1.0 for i in range(1, n)},
            "=",
            1.0,
            name="volta_depot",
        )
    )

    for i in range(1, n):
        for j in range(1, n):
            if i == j:
                continue
            constraints.append(
                Constraint(
                    {
                        f"u{i}": 1.0,
                        f"u{j}": -1.0,
                        f"x_{i}_{j}": float(n),
                    },
                    "<=",
                    float(n - 1),
                    name=f"mtz_{i}_{j}",
                )
            )

    return make_model(
        ObjectiveSense.MIN,
        objective,
        constraints,
        variables,
        f"TSP MTZ ({n} nós)",
    )

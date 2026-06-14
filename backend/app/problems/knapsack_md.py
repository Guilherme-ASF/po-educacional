from __future__ import annotations

from typing import Any

from app.models.problem import Constraint, ObjectiveSense
from app.problems._util import bin_vars, make_model

DEFAULT_INSTANCE: dict[str, Any] = {
    "banda": [30, 20, 45, 15, 35, 25, 40],
    "buffer": [8, 5, 10, 3, 9, 6, 7],
    "prioridade": [50, 30, 70, 20, 60, 40, 65],
    "cap_banda": 100,
    "cap_buffer": 25,
}


def build_model(data: dict[str, Any]) -> ProblemModel:
    banda = data["banda"]
    buffer = data["buffer"]
    prio = data["prioridade"]
    cap_b = float(data["cap_banda"])
    cap_u = float(data["cap_buffer"])
    n = len(prio)
    names = [f"x{j+1}" for j in range(n)]

    objective = {names[j]: float(prio[j]) for j in range(n)}
    constraints = [
        Constraint({names[j]: float(banda[j]) for j in range(n)}, "<=", cap_b, name="banda"),
        Constraint({names[j]: float(buffer[j]) for j in range(n)}, "<=", cap_u, name="buffer"),
    ]

    return make_model(
        ObjectiveSense.MAX,
        objective,
        constraints,
        bin_vars(names),
        f"Knapsack multidimensional ({n} fluxos)",
    )

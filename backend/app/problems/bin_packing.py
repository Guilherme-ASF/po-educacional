from __future__ import annotations

from typing import Any

from app.models.problem import Constraint, ObjectiveSense
from app.problems._util import bin_vars, make_model

DEFAULT_INSTANCE: dict[str, Any] = {
    "demandas": [4, 3, 5, 2, 4, 3],
    "capacidade": 10,
}


def build_model(data: dict[str, Any]) -> ProblemModel:
    demandas = data["demandas"]
    cap = float(data["capacidade"])
    n = len(demandas)
    n_bins = n  # upper bound on bins

    x_names = [f"x_{i}_{j}" for i in range(n) for j in range(n_bins)]
    y_names = [f"y{j+1}" for j in range(n_bins)]
    variables = bin_vars(x_names + y_names)

    objective = {y: 1.0 for y in y_names}
    constraints: list[Constraint] = []

    for i in range(n):
        constraints.append(
            Constraint({f"x_{i}_{j}": 1.0 for j in range(n_bins)}, "=", 1.0, name=f"assign_{i}")
        )

    for j in range(n_bins):
        load = {f"x_{i}_{j}": float(demandas[i]) for i in range(n)}
        load[y_names[j]] = -cap
        constraints.append(Constraint(load, "<=", 0.0, name=f"cap_{j}"))
        for i in range(n):
            constraints.append(
                Constraint({f"x_{i}_{j}": 1.0, y_names[j]: -1.0}, "<=", 0.0, name=f"link_{i}_{j}")
            )

    for j in range(1, n_bins):
        constraints.append(
            Constraint({y_names[j]: 1.0, y_names[j - 1]: -1.0}, "<=", 0.0, name=f"sym_{j}")
        )

    demand_total = sum(demandas)
    lb_bins = int(demand_total // cap) + (1 if demand_total % cap > 1e-9 else 0)
    constraints.append(
        Constraint({y: 1.0 for y in y_names}, ">=", float(lb_bins), name="min_bins_lb")
    )

    return make_model(
        ObjectiveSense.MIN,
        objective,
        constraints,
        variables,
        f"Bin packing ({n} VMs)",
    )

from __future__ import annotations

from typing import Any

from app.models.problem import Constraint, ObjectiveSense
from app.problems._util import cont_vars, int_vars, make_model, bin_vars

DEFAULT_INSTANCE: dict[str, Any] = {
    "tempos": [
        [4, 5, 3, 7],
        [3, 6, 4, 5],
        [5, 4, 6, 3],
    ],
    "capacidade": 12,
}


def build_model(data: dict[str, Any]) -> ProblemModel:
    from app.problems.multiprocessor_text import server_label, task_label, var_name

    tempos: list[list[float]] = data["tempos"]
    cap = float(data["capacidade"])
    n_srv = len(tempos)
    n_task = len(tempos[0])

    x_names = [
        var_name(task_label(i), server_label(j))
        for i in range(n_task)
        for j in range(n_srv)
    ]
    variables = bin_vars(x_names) + cont_vars(["M"])

    objective = {"M": 1.0}
    constraints: list[Constraint] = []

    for i in range(n_task):
        t = task_label(i)
        constraints.append(
            Constraint(
                {var_name(t, server_label(j)): 1.0 for j in range(n_srv)},
                "=",
                1.0,
                name=f"atrib_{t}",
            )
        )

    for j in range(n_srv):
        s = server_label(j)
        load = {var_name(task_label(i), s): tempos[j][i] for i in range(n_task)}
        constraints.append(Constraint(dict(load), "<=", cap, name=f"cap_{s}"))
        m_load = dict(load)
        m_load["M"] = -1.0
        constraints.append(Constraint(m_load, "<=", 0.0, name=f"make_{s}"))

    constraints.append(Constraint({"M": 1.0}, ">=", 0.0, name="m_nonneg"))

    return make_model(
        ObjectiveSense.MIN,
        objective,
        constraints,
        variables,
        f"Multiprocessador {n_srv}×{n_task} (min makespan)",
    )

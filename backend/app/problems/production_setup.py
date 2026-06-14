from __future__ import annotations

from typing import Any

from app.models.problem import Constraint, ObjectiveSense, Variable, VariableType
from app.problems._util import make_model

DEFAULT_INSTANCE: dict[str, Any] = {
    "setup": [200, 150, 300],
    "var_cost": [8, 6, 12],
    "receita": [20, 18, 30],
    "demanda_min": [10, 15, 8],
    "cap_unidades": 60,
    "cap_horas": 80,
    "horas": [1.0, 1.5, 2.0],
}


def build_model(data: dict[str, Any]) -> ProblemModel:
    setup = data["setup"]
    vc = data["var_cost"]
    rev = data["receita"]
    dem = data["demanda_min"]
    cap_u = float(data["cap_unidades"])
    cap_h = float(data["cap_horas"])
    horas = data["horas"]
    n = len(setup)
    M = cap_u

    q_names = [f"q{i+1}" for i in range(n)]
    y_names = [f"y{i+1}" for i in range(n)]
    variables = (
        [Variable(q, VariableType.CONTINUOUS) for q in q_names]
        + [Variable(y, VariableType.BINARY) for y in y_names]
    )

    objective = {y_names[i]: -float(setup[i]) for i in range(n)}
    for i in range(n):
        objective[q_names[i]] = float(rev[i] - vc[i])

    constraints: list[Constraint] = [
        Constraint({q_names[i]: 1.0 for i in range(n)}, "<=", cap_u, name="cap_prod"),
        Constraint(
            {q_names[i]: float(horas[i]) for i in range(n)}, "<=", cap_h, name="cap_horas"
        ),
    ]
    for i in range(n):
        constraints.append(
            Constraint({q_names[i]: 1.0}, ">=", float(dem[i]), name=f"dem_{i}")
        )
        constraints.append(
            Constraint({q_names[i]: 1.0, y_names[i]: -M}, "<=", 0.0, name=f"bigm_{i}")
        )

    return make_model(
        ObjectiveSense.MAX,
        objective,
        constraints,
        variables,
        "Produção com custo fixo de setup (PLIM)",
    )

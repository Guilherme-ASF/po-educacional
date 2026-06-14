from __future__ import annotations

from typing import Any

from app.models.problem import Constraint, ObjectiveSense
from app.problems._util import bin_vars, make_model

DEFAULT_INSTANCE: dict[str, Any] = {
    "custos": [80, 60, 90, 50, 70, 100],
    "impactos": [120, 85, 140, 60, 110, 160],
    "orcamento": 280,
}


def build_model(data: dict[str, Any]) -> ProblemModel:
    custos = data["custos"]
    impactos = data["impactos"]
    budget = float(data["orcamento"])
    n = len(custos)
    names = [f"x{i+1}" for i in range(n)]

    objective = {names[i]: float(impactos[i]) for i in range(n)}
    constraints = [
        Constraint({names[i]: float(custos[i]) for i in range(n)}, "<=", budget, name="orcamento"),
        Constraint({names[2]: 1.0, names[0]: -1.0}, "<=", 0.0, name="p3_implies_p1"),
        Constraint({names[3]: 1.0, names[4]: 1.0}, "<=", 1.0, name="p4_xor_p5"),
        Constraint({names[0]: 1.0, names[1]: 1.0, names[3]: 1.0}, ">=", 2.0, name="min_dois"),
    ]

    return make_model(
        ObjectiveSense.MAX,
        objective,
        constraints,
        bin_vars(names),
        "Seleção de projetos PIB",
    )

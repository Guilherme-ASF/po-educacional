from __future__ import annotations

from typing import Any

from app.models.problem import Constraint, ObjectiveSense
from app.problems._util import bin_vars, make_model

DEFAULT_INSTANCE: dict[str, Any] = {
    "salas": ["S1", "S2", "S3"],
    "horarios": ["H1", "H2", "H3", "H4"],
    "disciplinas": ["D1", "D2", "D3", "D4"],
    "pontuacoes": {
        ("D1", "S2", "H1"): 8,
        ("D1", "S2", "H2"): 7,
        ("D1", "S2", "H3"): 9,
        ("D1", "S3", "H1"): 8,
        ("D1", "S3", "H2"): 7,
        ("D1", "S3", "H3"): 9,
        ("D2", "S1", "H1"): 6,
        ("D2", "S1", "H2"): 8,
        ("D2", "S1", "H3"): 5,
        ("D2", "S1", "H4"): 7,
        ("D2", "S2", "H1"): 6,
        ("D2", "S2", "H2"): 8,
        ("D2", "S2", "H3"): 5,
        ("D2", "S2", "H4"): 7,
        ("D2", "S3", "H1"): 6,
        ("D2", "S3", "H2"): 8,
        ("D2", "S3", "H3"): 5,
        ("D2", "S3", "H4"): 7,
        ("D3", "S3", "H1"): 9,
        ("D3", "S3", "H2"): 6,
        ("D3", "S3", "H3"): 8,
        ("D3", "S3", "H4"): 7,
        ("D4", "S1", "H3"): 10,
        ("D4", "S1", "H4"): 9,
        ("D4", "S2", "H3"): 10,
        ("D4", "S2", "H4"): 9,
    },
}


def _v(d: str, s: str, h: str) -> str:
    return f"x_{d}_{s}_{h}"


def build_model(data: dict[str, Any]) -> ProblemModel:
    salas = data["salas"]
    horarios = data["horarios"]
    disciplinas = data["disciplinas"]
    pts: dict[tuple[str, str, str], int] = {
        tuple(k): v for k, v in data["pontuacoes"].items()
    }

    names: list[str] = []
    objective: dict[str, float] = {}
    for d in disciplinas:
        for s in salas:
            for h in horarios:
                key = (d, s, h)
                if key in pts:
                    nm = _v(d, s, h)
                    names.append(nm)
                    objective[nm] = float(pts[key])

    constraints: list[Constraint] = []

    for d in disciplinas:
        valid = [_v(d, s, h) for s in salas for h in horarios if (d, s, h) in pts]
        if valid:
            constraints.append(Constraint({v: 1.0 for v in valid}, "=", 1.0, name=f"uma_{d}"))

    for s in salas:
        for h in horarios:
            coefs = {
                _v(d, s, h): 1.0
                for d in disciplinas
                if (d, s, h) in pts
            }
            if len(coefs) > 1:
                constraints.append(Constraint(coefs, "<=", 1.0, name=f"slot_{s}_{h}"))

    # D1 não em H4
    for s in salas:
        if ( "D1", s, "H4") in pts or _v("D1", s, "H4") in names:
            pass
    for s in salas:
        v = _v("D1", s, "H4")
        if v in names:
            constraints.append(Constraint({v: 1.0}, "=", 0.0, name="d1_no_h4"))

    # D3 só S3
    for s in salas:
        if s == "S3":
            continue
        for h in horarios:
            v = _v("D3", s, h)
            if v in names:
                constraints.append(Constraint({v: 1.0}, "=", 0.0, name=f"d3_s3_{s}_{h}"))

    # D4 só S1 ou S2
    for s in ["S3"]:
        for h in horarios:
            v = _v("D4", s, h)
            if v in names:
                constraints.append(Constraint({v: 1.0}, "=", 0.0, name=f"d4_s12_{h}"))

    # D4 só H3 ou H4
    for h in ["H1", "H2"]:
        for s in salas:
            v = _v("D4", s, h)
            if v in names:
                constraints.append(Constraint({v: 1.0}, "=", 0.0, name=f"d4_h34_{s}_{h}"))

    # D3 não compartilha horário com D1
    for h in horarios:
        coefs = {}
        for s in salas:
            v1 = _v("D1", s, h)
            v3 = _v("D3", s, h)
            if v1 in names:
                coefs[v1] = 1.0
            if v3 in names:
                coefs[v3] = 1.0
        if len(coefs) >= 2:
            constraints.append(Constraint(coefs, "<=", 1.0, name=f"conf_d1_d3_{h}"))

    # D2 precede D4: sum_h t_h*x_D2 <= sum_h t_h*x_D4 (simplificado: índice horário)
    h_idx = {h: i for i, h in enumerate(horarios)}
    lhs: dict[str, float] = {}
    rhs: dict[str, float] = {}
    for s in salas:
        for h in horarios:
            v2 = _v("D2", s, h)
            v4 = _v("D4", s, h)
            if v2 in names:
                lhs[v2] = float(h_idx[h])
            if v4 in names:
                rhs[v4] = float(h_idx[h])
    if lhs and rhs:
        comb = {k: lhs.get(k, 0) - rhs.get(k, 0) for k in set(lhs) | set(rhs)}
        constraints.append(Constraint(comb, "<=", 0.0, name="d2_antes_d4"))

    return make_model(
        ObjectiveSense.MAX,
        objective,
        constraints,
        bin_vars(names),
        "Grade de horários (timetabling)",
    )

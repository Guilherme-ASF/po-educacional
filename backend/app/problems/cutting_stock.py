from __future__ import annotations

from typing import Any

from app.models.problem import Constraint, ObjectiveSense
from app.problems._util import int_vars, make_model

DEFAULT_INSTANCE: dict[str, Any] = {
    "comprimentos": [45, 30, 25, 20, 15],
    "demandas": [4, 6, 5, 8, 10],
    "bloco": 100,
}


def _gerar_padroes(comprimentos: list[int], bloco: int) -> list[list[int]]:
    """Gera padrões factíveis (single-type + combinações gulosas, máx. ~25)."""
    n = len(comprimentos)
    padroes: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()

    def add(pat: list[int]) -> None:
        if sum(pat) == 0 or sum(pat) > bloco:
            return
        key = tuple(pat)
        if key not in seen:
            seen.add(key)
            padroes.append(pat)

    for r in range(n):
        q = bloco // comprimentos[r]
        if q > 0:
            pat = [0] * n
            pat[r] = q
            add(pat)

    for r in range(n):
        resto = bloco - comprimentos[r]
        if resto <= 0:
            continue
        for s in range(n):
            if comprimentos[s] <= resto:
                pat = [0] * n
                pat[r] = 1
                pat[s] = resto // comprimentos[s]
                if pat[s] * comprimentos[s] <= resto:
                    add(pat)

    def rec(idx: int, resto: int, atual: list[int]) -> None:
        if len(padroes) >= 25:
            return
        if idx == n:
            add(atual)
            return
        max_q = resto // comprimentos[idx] if comprimentos[idx] else 0
        for q in range(max_q, -1, -1):
            atual.append(q)
            rec(idx + 1, resto - q * comprimentos[idx], atual)
            atual.pop()

    rec(0, bloco, [])
    # padrões unitários mínimos para garantir factibilidade
    for r in range(n):
        for q in range(1, bloco // comprimentos[r] + 1):
            pat = [0] * n
            pat[r] = q
            if sum(pat[i] * comprimentos[i] for i in range(n)) <= bloco:
                add(pat)
    return padroes[:30]


def build_model(data: dict[str, Any]) -> ProblemModel:
    comp = [int(c) for c in data["comprimentos"]]
    dem = [int(d) for d in data["demandas"]]
    bloco = int(data["bloco"])
    padroes = _gerar_padroes(comp, bloco)
    n_types = len(comp)

    z_names = [f"z{p+1}" for p in range(len(padroes))]
    variables = int_vars(z_names)

    objective = {z: 1.0 for z in z_names}
    constraints: list[Constraint] = []

    for r in range(n_types):
        coefs = {z_names[p]: float(padroes[p][r]) for p in range(len(padroes))}
        constraints.append(Constraint(coefs, ">=", float(dem[r]), name=f"dem_{r+1}"))

    for z in z_names:
        constraints.append(Constraint({z: 1.0}, ">=", 0.0, name=f"nn_{z}"))

    return make_model(
        ObjectiveSense.MIN,
        objective,
        constraints,
        variables,
        f"Cutting stock ({n_types} tipos, {len(padroes)} padrões)",
    )

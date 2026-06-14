from __future__ import annotations

import itertools
from typing import Any


def _slots_for_discipline(
    d: str,
    data: dict[str, Any],
) -> list[tuple[str, str, float]]:
    salas = data["salas"]
    horarios = data["horarios"]
    pts: dict[tuple[str, str, str], int] = {
        tuple(k): v for k, v in data["pontuacoes"].items()
    }
    out: list[tuple[str, str, float]] = []
    for s in salas:
        for h in horarios:
            key = (d, s, h)
            if key in pts:
                out.append((s, h, float(pts[key])))
    return out


def solve_timetabling_brute(data: dict[str, Any]) -> tuple[dict[str, float], float]:
    """Enumera combinações factíveis (4 disciplinas, instância do enunciado)."""
    disciplinas: list[str] = data["disciplinas"]
    horarios: list[str] = data["horarios"]
    h_idx = {h: i for i, h in enumerate(horarios)}

    options = {d: _slots_for_discipline(d, data) for d in disciplinas}
    best_score = -1.0
    best_choices: dict[str, tuple[str, str, float]] = {}

    for combo in itertools.product(*(options[d] for d in disciplinas)):
        choice = dict(zip(disciplinas, combo))
        slots_used: set[tuple[str, str]] = set()
        ok = True
        for d in disciplinas:
            s, h, _ = choice[d]
            if (s, h) in slots_used:
                ok = False
                break
            slots_used.add((s, h))
        if not ok:
            continue

        d1_h = choice["D1"][1]
        d3_h = choice["D3"][1]
        if d1_h == d3_h:
            continue

        d2_h = choice["D2"][1]
        d4_h = choice["D4"][1]
        if h_idx[d2_h] > h_idx[d4_h]:
            continue

        score = sum(choice[d][2] for d in disciplinas)
        if score > best_score:
            best_score = score
            best_choices = choice

    sol: dict[str, float] = {}
    for d in disciplinas:
        s, h, _ = best_choices[d]
        sol[f"x_{d}_{s}_{h}"] = 1.0

    return sol, best_score

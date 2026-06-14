from __future__ import annotations

import itertools
from typing import Any


def solve_multiprocessor_brute(data: dict[str, Any]) -> tuple[dict[str, float], float]:
    """Enumera atribuições (n_task^n_srv pequeno)."""
    tempos: list[list[float]] = data["tempos"]
    cap = float(data["capacidade"])
    n_srv = len(tempos)
    n_task = len(tempos[0])

    best_m = float("inf")
    best_assign: tuple[int, ...] = tuple()

    for assign in itertools.product(range(n_srv), repeat=n_task):
        loads = [0.0] * n_srv
        ok = True
        for i, j in enumerate(assign):
            loads[j] += tempos[j][i]
            if loads[j] > cap + 1e-9:
                ok = False
                break
        if not ok:
            continue
        m = max(loads)
        if m < best_m:
            best_m = m
            best_assign = assign

    from app.problems.multiprocessor_text import server_label, task_label, var_name

    sol: dict[str, float] = {
        var_name(task_label(i), server_label(j)): 0.0
        for i in range(n_task)
        for j in range(n_srv)
    }
    for i, j in enumerate(best_assign):
        sol[var_name(task_label(i), server_label(j))] = 1.0
    sol["M"] = best_m
    return sol, best_m

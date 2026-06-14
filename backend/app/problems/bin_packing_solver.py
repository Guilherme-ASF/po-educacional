from __future__ import annotations

import itertools
from typing import Any


def _pack_with_k(demandas: list[int], cap: int, k: int) -> list[int] | None:
    """Retorna atribuição item->bin (0..k-1) ou None se impossível."""
    n = len(demandas)
    order = sorted(range(n), key=lambda i: demandas[i], reverse=True)

    def backtrack(idx: int, loads: list[float], assign: list[int]) -> bool:
        if idx == n:
            return True
        i = order[idx]
        d = demandas[i]
        for b in range(k):
            if loads[b] + d <= cap + 1e-9:
                loads[b] += d
                assign[i] = b
                if backtrack(idx + 1, loads, assign):
                    return True
                loads[b] -= d
        return False

    loads = [0.0] * k
    assign = [-1] * n
    if backtrack(0, loads, assign):
        return assign
    return None


def solve_bin_packing_exact(data: dict[str, Any]) -> tuple[dict[str, float], float]:
    """Número mínimo de bins por busca crescente + backtracking (instâncias pequenas)."""
    demandas = [int(d) for d in data["demandas"]]
    cap = int(data["capacidade"])
    n = len(demandas)
    total = sum(demandas)
    lb = (total + cap - 1) // cap

    assignment: list[int] | None = None
    k_opt = n
    for k in range(lb, n + 1):
        assignment = _pack_with_k(demandas, cap, k)
        if assignment is not None:
            k_opt = k
            break

    if assignment is None:
        assignment = list(range(n))

    sol: dict[str, float] = {}
    for i in range(n):
        for j in range(n):
            sol[f"x_{i}_{j}"] = 1.0 if assignment[i] == j else 0.0
    for j in range(n):
        sol[f"y{j + 1}"] = 1.0 if j < k_opt else 0.0

    return sol, float(k_opt)

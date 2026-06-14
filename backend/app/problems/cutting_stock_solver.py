from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.problems.cutting_stock import _gerar_padroes


def solve_cutting_stock_greedy(data: dict[str, Any]) -> tuple[dict[str, float], float]:
    """Programação dinâmica sobre demanda restante (instâncias pequenas)."""
    comp = [int(c) for c in data["comprimentos"]]
    dem = [int(d) for d in data["demandas"]]
    bloco = int(data["bloco"])
    padroes = _gerar_padroes(comp, bloco)
    n_types = len(comp)
    n_pat = len(padroes)

    start = tuple(dem)
    parent: dict[tuple[int, ...], tuple[tuple[int, ...], int]] = {}

    @lru_cache(maxsize=None)
    def min_rolls(rem: tuple[int, ...]) -> int:
        if all(r <= 0 for r in rem):
            return 0
        best = 10**9
        for p in range(n_pat):
            new = tuple(max(0, rem[r] - padroes[p][r]) for r in range(n_types))
            if new == rem:
                continue
            sub = min_rolls(new)
            cand = sub + 1
            if cand < best:
                best = cand
                parent[rem] = (new, p)
        return best

    z = float(min_rolls(start))
    if z >= 10**9:
        zvals = [0] * n_pat
        for r in range(n_types):
            for p in range(n_pat):
                if padroes[p][r] > 0:
                    need = (dem[r] + padroes[p][r] - 1) // padroes[p][r]
                    zvals[p] = max(zvals[p], need)
        return {f"z{p + 1}": float(zvals[p]) for p in range(n_pat)}, float(sum(zvals))

    zvals = [0] * n_pat
    cur = start
    while cur in parent:
        nxt, p = parent[cur]
        zvals[p] += 1
        cur = nxt

    return {f"z{p + 1}": float(zvals[p]) for p in range(n_pat)}, z

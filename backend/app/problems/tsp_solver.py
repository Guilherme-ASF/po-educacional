from __future__ import annotations

from itertools import permutations


def solve_tsp_brute_force(distancias: list[list[float]]) -> tuple[dict[str, float], float]:
    """TSP exato por enumeração (n <= 10)."""
    n = len(distancias)
    best_cost = float("inf")
    best_tour: list[int] = []

    for perm in permutations(range(1, n)):
        tour = [0, *perm, 0]
        cost = sum(distancias[tour[i]][tour[i + 1]] for i in range(len(tour) - 1))
        if cost < best_cost:
            best_cost = cost
            best_tour = tour

    sol: dict[str, float] = {}
    for i in range(n):
        for j in range(n):
            if i != j:
                sol[f"x_{i}_{j}"] = 0.0
    for k in range(len(best_tour) - 1):
        sol[f"x_{best_tour[k]}_{best_tour[k + 1]}"] = 1.0

    return sol, float(best_cost)

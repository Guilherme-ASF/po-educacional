from __future__ import annotations

from itertools import combinations

import numpy as np

from app.models.problem import ObjectiveSense, ProblemModel


def solve_by_vertices(problem: ProblemModel) -> tuple[dict[str, float], float] | None:
    """Resolve PL por enumeração de vértices (até 8 variáveis)."""
    if problem.n_vars > 8:
        return None

    n = problem.n_vars
    names = problem.var_names
    halfspaces: list[tuple[np.ndarray, float]] = []

    for cst in problem.constraints:
        a = np.array([cst.coefficients.get(v, 0.0) for v in names], dtype=float)
        b = float(cst.rhs)
        if cst.sense == "<=":
            halfspaces.append((a, b))
        elif cst.sense == ">=":
            halfspaces.append((-a, -b))
        else:
            halfspaces.append((a, b))
            halfspaces.append((-a, -b))

    for i in range(n):
        row = np.zeros(n)
        row[i] = -1.0
        halfspaces.append((row, 0.0))

    m = len(halfspaces)
    best_sol: dict[str, float] | None = None
    best_z = -np.inf if problem.objective_sense == ObjectiveSense.MAX else np.inf

    for idxs in combinations(range(m), n):
        A = np.array([halfspaces[i][0] for i in idxs], dtype=float)
        b = np.array([halfspaces[i][1] for i in idxs], dtype=float)
        if abs(np.linalg.det(A)) < 1e-10:
            continue
        try:
            x = np.linalg.solve(A, b)
        except np.linalg.LinAlgError:
            continue

        if not _is_feasible(x, names, problem):
            continue

        z = sum(problem.objective.get(v, 0) * x[j] for j, v in enumerate(names))
        if problem.objective_sense == ObjectiveSense.MAX:
            if z > best_z + 1e-9:
                best_z = z
                best_sol = {names[j]: float(x[j]) for j in range(n)}
        else:
            if z < best_z - 1e-9:
                best_z = z
                best_sol = {names[j]: float(x[j]) for j in range(n)}

    if best_sol is None:
        return None
    return best_sol, float(best_z)


def _is_feasible(x: np.ndarray, names: list[str], problem: ProblemModel) -> bool:
    sol = {names[i]: x[i] for i in range(len(names))}
    if np.any(x < -1e-6):
        return False
    for cst in problem.constraints:
        lhs = sum(cst.coefficients.get(v, 0) * sol[v] for v in names)
        if cst.sense == "<=" and lhs > cst.rhs + 1e-6:
            return False
        if cst.sense == ">=" and lhs < cst.rhs - 1e-6:
            return False
        if cst.sense == "=" and abs(lhs - cst.rhs) > 1e-6:
            return False
    return True

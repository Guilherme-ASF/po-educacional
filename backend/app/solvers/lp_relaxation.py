from __future__ import annotations

from app.models.problem import ObjectiveSense, ProblemModel, VariableType


def solve_lp_relaxation(problem: ProblemModel) -> tuple[dict[str, float], float] | None:
    """Resolve relaxação LP (variáveis contínuas) via scipy.optimize.linprog."""
    try:
        from scipy.optimize import linprog
    except ImportError:
        return None

    names = problem.var_names
    n = len(names)
    if n == 0:
        return None

    c = [problem.objective.get(v, 0.0) for v in names]
    if problem.objective_sense == ObjectiveSense.MAX:
        c = [-x for x in c]

    a_ub: list[list[float]] = []
    b_ub: list[float] = []
    a_eq: list[list[float]] = []
    b_eq: list[float] = []

    for cst in problem.constraints:
        row = [cst.coefficients.get(v, 0.0) for v in names]
        if cst.sense == "<=":
            a_ub.append(row)
            b_ub.append(float(cst.rhs))
        elif cst.sense == ">=":
            a_ub.append([-x for x in row])
            b_ub.append(float(-cst.rhs))
        else:
            a_eq.append(row)
            b_eq.append(float(cst.rhs))

    bounds: list[tuple[float, float | None]] = []
    for var in problem.variables:
        if var.var_type == VariableType.BINARY:
            bounds.append((0.0, 1.0))
        else:
            bounds.append((0.0, None))

    res = linprog(
        c,
        A_ub=a_ub if a_ub else None,
        b_ub=b_ub if b_ub else None,
        A_eq=a_eq if a_eq else None,
        b_eq=b_eq if b_eq else None,
        bounds=bounds,
        method="highs",
    )
    if not res.success or res.x is None:
        return None

    sol = {names[i]: float(res.x[i]) for i in range(n)}
    z = float(res.fun)
    if problem.objective_sense == ObjectiveSense.MAX:
        z = -z
    return sol, z

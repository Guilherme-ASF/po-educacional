from __future__ import annotations

from app.models.problem import ObjectiveSense, ProblemModel


def model_to_latex(problem: ProblemModel) -> str:
    sense = "\\max" if problem.objective_sense == ObjectiveSense.MAX else "\\min"
    obj_terms = []
    for v, c in problem.objective.items():
        if c == 0:
            continue
        if c == 1:
            obj_terms.append(v.replace("x", "x_") if "x" in v else v)
        elif c == -1:
            obj_terms.append(f"-{v.replace('x', 'x_')}")
        else:
            obj_terms.append(f"{_fmt(c)}{v.replace('x', 'x_')}")

    obj = " + ".join(obj_terms).replace("+ -", "- ")

    lines = [f"{sense} \\; Z = {obj}", "\\text{sujeito a}"]
    for cst in problem.constraints:
        terms = []
        for v, c in cst.coefficients.items():
            vn = v.replace("x", "x_")
            if c == 1:
                terms.append(vn)
            elif c == -1:
                terms.append(f"-{vn}")
            else:
                terms.append(f"{_fmt(c)}{vn}")
        lhs = " + ".join(terms).replace("+ -", "- ")
        op = {"<=": "\\leq", ">=": "\\geq", "=": "="}[cst.sense]
        lines.append(f"{lhs} {op} {_fmt(cst.rhs)}")

    var_lines = []
    for var in problem.variables:
        vn = var.name.replace("x", "x_")
        if var.var_type.value == "binary":
            var_lines.append(f"{vn} \\in \\{{0,1\\}}")
        elif var.var_type.value == "integer":
            var_lines.append(f"{vn} \\in \\mathbb{{Z}}_{{\\geq 0}}")
        else:
            var_lines.append(f"{vn} \\geq 0")
    lines.append(", \\quad ".join(var_lines))
    return " \\\\ ".join(lines)


def interpret_problem(problem: ProblemModel) -> str:
    sense = "maximizar" if problem.objective_sense == ObjectiveSense.MAX else "minimizar"
    obj_desc = ", ".join(
        f"{_fmt(c)}·{v}" for v, c in problem.objective.items() if c != 0
    )
    parts = [
        f"Trata-se de um problema de otimização linear cujo objetivo é {sense} "
        f"Z = {obj_desc}.",
        f"O modelo possui {problem.n_vars} variável(is) de decisão e "
        f"{problem.n_constraints} restrição(ões).",
    ]
    if problem.description:
        parts.insert(0, f"Contexto: {problem.description[:200]}")
    return " ".join(parts)


def _fmt(val: float) -> str:
    if val == int(val):
        return str(int(val))
    return f"{val:g}"

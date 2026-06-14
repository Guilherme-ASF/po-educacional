from __future__ import annotations

import re

from app.models.problem import ObjectiveSense, ProblemModel


def var_to_text(name: str) -> str:
    if not name or (name.isupper() and len(name) <= 2):
        return name
    m = re.match(r"^([a-zA-Z]+)(.*)$", name)
    if not m:
        return name
    base, rest = m.group(1), m.group(2)
    if not rest:
        return name
    if rest.startswith("_"):
        parts = [p for p in rest.split("_") if p]
        if not parts:
            return name
        if len(parts) == 1 and parts[0].isdigit():
            return f"{base}{parts[0]}"
        return f"{base}_" + "_".join(parts)
    if rest.isdigit():
        return f"{base}{rest}"
    return name


def var_to_latex(name: str) -> str:
    if not name or (name.isupper() and len(name) <= 2):
        return name
    m = re.match(r"^([a-zA-Z]+)(.*)$", name)
    if not m:
        return name
    base, rest = m.group(1), m.group(2)
    if not rest:
        return name
    if rest.startswith("_"):
        parts = [p for p in rest.split("_") if p]
        if not parts:
            return name
        if len(parts) == 1:
            p = parts[0]
            return f"{base}_{p}" if len(p) == 1 else f"{base}_{{{p}}}"
        return f"{base}_{{{','.join(parts)}}}"
    if rest.isdigit():
        return f"{base}_{rest}" if len(rest) == 1 else f"{base}_{{{rest}}}"
    return name


def _term_text(coef: float, var: str) -> str:
    vn = var_to_text(var)
    if coef == 1:
        return vn
    if coef == -1:
        return f"-{vn}"
    fc = _fmt(abs(coef))
    return f"-{fc}{vn}" if coef < 0 else f"{fc}{vn}"


def _join_terms(terms: list[str]) -> str:
    if not terms:
        return "0"
    out = terms[0]
    for t in terms[1:]:
        if t.startswith("-"):
            out += f" - {t[1:]}"
        else:
            out += f" + {t}"
    return out


def _is_redundant_nonneg(cst) -> bool:
    if cst.sense != ">=" or abs(cst.rhs) > 1e-9:
        return False
    if len(cst.coefficients) != 1:
        return False
    return abs(next(iter(cst.coefficients.values())) - 1.0) < 1e-9


def model_to_text(problem: ProblemModel) -> str:
    sense = "Max" if problem.objective_sense == ObjectiveSense.MAX else "Min"
    obj_terms = [_term_text(c, v) for v, c in problem.objective.items() if c != 0]
    lines = [f"{sense} Z = {_join_terms(obj_terms)}", "", "S.A.", ""]

    for cst in problem.constraints:
        if _is_redundant_nonneg(cst):
            continue
        terms = [_term_text(c, v) for v, c in cst.coefficients.items() if c != 0]
        lines.append(f"{_join_terms(terms)} {cst.sense} {_fmt(cst.rhs)}")

    lines.append("")
    cont: list[str] = []
    integer: list[str] = []
    binary: list[str] = []
    for var in problem.variables:
        vn = var_to_text(var.name)
        if var.var_type.value == "binary":
            binary.append(vn)
        elif var.var_type.value == "integer":
            integer.append(vn)
        else:
            cont.append(vn)

    if cont:
        lines.append(", ".join(cont) + " >= 0")
    if integer:
        lines.append(", ".join(integer) + " inteiro")
    if binary:
        lines.append(", ".join(binary) + " binário")

    return "\n".join(lines)


def model_to_latex(problem: ProblemModel) -> str:
    sense = "\\max" if problem.objective_sense == ObjectiveSense.MAX else "\\min"
    obj_terms = []
    for v, c in problem.objective.items():
        if c == 0:
            continue
        vn = var_to_latex(v)
        if c == 1:
            obj_terms.append(vn)
        elif c == -1:
            obj_terms.append(f"-{vn}")
        else:
            obj_terms.append(f"{_fmt(c)}{vn}")

    obj = " + ".join(obj_terms).replace("+ -", "- ")
    lines = [f"{sense} \\; Z = {obj}", "\\text{sujeito a}"]
    for cst in problem.constraints:
        terms = []
        for v, c in cst.coefficients.items():
            vn = var_to_latex(v)
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
        vn = var_to_latex(var.name)
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

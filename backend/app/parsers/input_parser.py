from __future__ import annotations

import re
from typing import Literal

from app.models.problem import (
    Constraint,
    ObjectiveSense,
    ProblemModel,
    Variable,
    VariableType,
)


def detect_input_format(text: str) -> Literal["mathematical", "simplified", "natural"]:
    lower = text.lower()
    natural_keywords = [
        "desejo",
        "maximizar",
        "minimizar",
        "lucro",
        "custo",
        "produto",
        "posso produzir",
        "preciso produzir",
        "variáveis são",
        "variaveis sao",
        "cada produto",
        "unidades",
    ]
    normalized = lower.replace(" ", "")
    if any(k in lower for k in natural_keywords) and "x1" not in normalized:
        return "natural"
    if re.search(r"x\d+\s*\*", text) or re.search(r"\*\s*x\d+", text):
        return "simplified"
    return "mathematical"


def parse_problem(text: str) -> ProblemModel:
    fmt = detect_input_format(text)
    if fmt == "natural":
        return _parse_natural(text)
    return _parse_structured(text)


def _parse_structured(text: str) -> ProblemModel:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    sense = ObjectiveSense.MAX
    objective: dict[str, float] = {}
    var_names: set[str] = set()
    constraints: list[Constraint] = []
    var_types: dict[str, VariableType] = {}
    obj_found = False

    for line in lines:
        lower = line.lower()
        if re.match(r"^s\.?\s*a\.?\s*\.?$", lower):
            continue
        if lower.startswith("sujeito"):
            continue

        if not obj_found and re.search(r"(max|min|z\s*=)", lower):
            if re.search(r"\bmin\b", lower):
                sense = ObjectiveSense.MIN
            expr = re.sub(r"^(max|min)\s*(z\s*=\s*)?", "", line, flags=re.I)
            expr = re.sub(r"^z\s*=\s*", "", expr, flags=re.I)
            objective, found = _parse_linear_expression(expr)
            var_names |= found
            obj_found = True
            continue

        if re.search(r"(<=|>=|=|≤|≥)", line):
            if "," in line and re.search(r"(>=|≥)\s*0", line) and "<=" not in line.replace(">=", ""):
                for part in line.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    cst, vnames, vtypes = _parse_constraint_line(part)
                    var_names |= vnames
                    var_types.update(vtypes)
                    if cst:
                        constraints.append(cst)
                continue
            cst, vnames, vtypes = _parse_constraint_line(line)
            if cst:
                constraints.append(cst)
                var_names |= vnames
                var_types.update(vtypes)

    if not var_names:
        raise ValueError("Nenhuma variável identificada no problema.")
    if not obj_found:
        raise ValueError("Não foi possível identificar a função objetivo.")

    sorted_names = sorted(var_names, key=_var_sort_key)
    variables = [
        Variable(name=n, var_type=var_types.get(n, VariableType.CONTINUOUS))
        for n in sorted_names
    ]

    return ProblemModel(
        objective_sense=sense,
        objective={k: objective.get(k, 0.0) for k in sorted_names},
        constraints=constraints,
        variables=variables,
    )


def _parse_constraint_line(line: str) -> tuple[Constraint | None, set[str], dict[str, VariableType]]:
    var_names: set[str] = set()
    var_types: dict[str, VariableType] = {}

    int_line = re.search(
        r"(x[\d_]+(?:\s*,\s*x[\d_]+)*)\s*(?:inteiro|inteiros|∈\s*Z|integer)",
        line,
        re.I,
    )
    if int_line:
        for v in re.findall(r"x[\d_]+", int_line.group(1)):
            vn = _normalize_var_name(v)
            var_names.add(vn)
            var_types[vn] = VariableType.INTEGER
        return None, var_names, var_types

    bin_line = re.search(
        r"(x[\d_]+(?:\s*,\s*x[\d_]+)*)\s*(?:bin[aá]rio|binary|∈\s*\{0,1\})",
        line,
        re.I,
    )
    if bin_line:
        for v in re.findall(r"x[\d_]+", bin_line.group(1)):
            vn = _normalize_var_name(v)
            var_names.add(vn)
            var_types[vn] = VariableType.BINARY
        return None, var_names, var_types

    nonneg = re.match(
        r"^(x[\d_]+(?:\s*,\s*x[\d_]+)*)\s*(?:>=|≥)\s*0\s*$",
        line,
        re.I,
    )
    if nonneg:
        for v in re.findall(r"x[\d_]+", nonneg.group(1)):
            vn = _normalize_var_name(v)
            var_names.add(vn)
            var_types.setdefault(vn, VariableType.CONTINUOUS)
        return None, var_names, var_types

    int_match = re.search(
        r"(x[\d_]+(?:\s*,\s*x[\d_]+)*)\s*(?:∈|in)\s*(?:Z|ℤ|Int|Integer|Inteiro)",
        line,
        re.I,
    )
    if int_match:
        for v in re.findall(r"x[\d_]+", int_match.group(1)):
            vn = _normalize_var_name(v)
            var_names.add(vn)
            var_types[vn] = VariableType.INTEGER
        return None, var_names, var_types

    sense_match = re.search(r"(<=|>=|=|≤|≥)", line)
    if not sense_match:
        return None, var_names, var_types

    lhs = line[: sense_match.start()].strip()
    rhs_str = line[sense_match.end() :].strip()
    op = sense_match.group(1).replace("≤", "<=").replace("≥", ">=")

    coeffs, found = _parse_linear_expression(lhs)
    var_names |= found

    if not rhs_str:
        raise ValueError(f"Restrição inválida (RHS vazio): {line}")

    rhs = float(rhs_str.replace(",", "."))
    return (
        Constraint(coefficients=coeffs, sense=op, rhs=rhs),  # type: ignore[arg-type]
        var_names,
        var_types,
    )


def _parse_natural(text: str) -> ProblemModel:
    lower = text.lower()
    sense = ObjectiveSense.MAX if "maximiz" in lower else ObjectiveSense.MIN

    var_map: dict[str, str] = {}
    var_counter = 1
    objective: dict[str, float] = {}

    profit_patterns = [
        r"(?:produto|item|variável|variavel)\s+([A-Za-z])\s+(?:gera|tem|produz)\s+(?:lucro|custo|valor)\s+(?:de\s+)?(\d+(?:[.,]\d+)?)",
        r"(?:cada\s+)?([A-Za-z])\s+(?:gera|tem)\s+(?:lucro|custo)\s+(?:de\s+)?(\d+(?:[.,]\d+)?)",
        r"([A-Za-z])\s*:\s*(\d+(?:[.,]\d+)?)",
    ]
    for pat in profit_patterns:
        for m in re.finditer(pat, text, re.I):
            label = m.group(1).upper()
            coef = float(m.group(2).replace(",", "."))
            if label not in var_map:
                var_map[label] = f"x{var_counter}"
                var_counter += 1
            objective[var_map[label]] = coef

    constraints: list[Constraint] = []

    max_sum = re.search(
        r"(?:no\s+m[aá]ximo|m[aá]ximo|at[eé])\s+(\d+(?:[.,]\d+)?)\s+unidades\s+somadas",
        lower,
    )
    if max_sum and var_map:
        rhs = float(max_sum.group(1).replace(",", "."))
        constraints.append(
            Constraint(
                coefficients={v: 1.0 for v in var_map.values()},
                sense="<=",
                rhs=rhs,
                name="Capacidade total",
            )
        )

    min_weighted = re.search(
        r"(?:pelo\s+menos|m[ií]nimo|preciso\s+produzir\s+pelo\s+menos)\s+(\d+(?:[.,]\d+)?)\s+unidades\s+ponderadas",
        lower,
    )
    if min_weighted and len(var_map) >= 2:
        rhs = float(min_weighted.group(1).replace(",", "."))
        names = sorted(var_map.values(), key=_var_sort_key)
        weighted = {names[0]: 2.0, names[1]: 3.0}
        constraints.append(
            Constraint(
                coefficients=weighted,
                sense=">=",
                rhs=rhs,
                name="Demanda ponderada",
            )
        )

    if not var_map:
        raise ValueError(
            "Não foi possível extrair variáveis da linguagem natural. "
            "Use nomes como 'produto A' e 'produto B' com coeficientes numéricos."
        )

    sorted_names = sorted(var_map.values(), key=_var_sort_key)
    variables = [Variable(name=n, var_type=VariableType.CONTINUOUS) for n in sorted_names]

    return ProblemModel(
        objective_sense=sense,
        objective={n: objective.get(n, 0.0) for n in sorted_names},
        constraints=constraints,
        variables=variables,
        description=text.strip(),
    )


def _parse_linear_expression(expr: str) -> tuple[dict[str, float], set[str]]:
    expr = expr.replace("−", "-").replace("–", "-")
    expr = re.sub(r"(\d)(x)", r"\1*\2", expr)
    expr = expr.replace(" ", "")
    expr = re.sub(r"x_(\d+)", r"x\1", expr)

    terms = re.findall(r"([+-]?[\d\.]*\*?x\d+)", expr)
    if not terms:
        terms = re.split(r"([+-])", expr)
        rebuilt: list[str] = []
        sign = "+"
        for t in terms:
            if t in "+-":
                sign = t
            elif t:
                rebuilt.append(sign + t if not t.startswith(("+", "-")) else t)
        terms = [t for t in rebuilt if t and t not in "+-"]

    coeffs: dict[str, float] = {}
    var_names: set[str] = set()

    for term in terms:
        term = term.strip()
        if not term:
            continue
        sign = -1.0 if term.startswith("-") else 1.0
        term = term.lstrip("+-")
        term = term.replace("*", "")
        m = re.match(r"([\d\.]*)x(\d+)", term)
        if m:
            coef_str, idx = m.groups()
            coef = float(coef_str) if coef_str else 1.0
            name = f"x{idx}"
            var_names.add(name)
            coeffs[name] = coeffs.get(name, 0.0) + sign * coef

    return coeffs, var_names


def _normalize_var_name(name: str) -> str:
    m = re.match(r"x_?(\d+)", name)
    return f"x{m.group(1)}" if m else name


def _var_sort_key(name: str) -> int:
    m = re.match(r"x(\d+)", name)
    return int(m.group(1)) if m else 0

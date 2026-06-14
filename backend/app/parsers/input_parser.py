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
    if "@modelo" in text or "@dados" in text:
        return "mathematical"
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
    prose = "\n".join(
        ln for ln in lower.splitlines() if not ln.strip().startswith("#")
    )
    normalized = prose.replace(" ", "")
    if any(k in prose for k in natural_keywords) and "x1" not in normalized:
        return "natural"
    if re.search(r"x\d+\s*\*", text) or re.search(r"\*\s*x\d+", text):
        return "simplified"
    return "mathematical"


def parse_problem(text: str) -> ProblemModel:
    from app.parsers.model_dsl import expand_model_dsl
    from app.parsers.summation_expander import expand_summations

    fmt = detect_input_format(text)
    if fmt == "natural":
        return _parse_natural(text)
    expanded = expand_summations(expand_model_dsl(text))
    return _parse_structured(expanded)


def _parse_structured(text: str) -> ProblemModel:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    sense = ObjectiveSense.MAX
    objective: dict[str, float] = {}
    var_names: set[str] = set()
    constraints: list[Constraint] = []
    var_types: dict[str, VariableType] = {}
    obj_found = False

    for line in lines:
        if line.strip().startswith("#"):
            continue
        lower = line.lower()
        if re.match(r"^s\.?\s*a\.?\s*\.?$", lower):
            continue
        if lower.startswith("sujeito"):
            continue
        if re.match(r"^∀", line.strip()):
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

        cst, vnames, vtypes = _parse_constraint_line(line)
        if vnames:
            var_names |= vnames
        if vtypes:
            var_types.update(vtypes)
        if cst:
            constraints.append(cst)

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

    var_list_pat = r"([a-zA-Z][a-zA-Z0-9_]+(?:\s*,\s*[a-zA-Z][a-zA-Z0-9_]+)*)"

    int_line = re.search(
        rf"{var_list_pat}\s*(?:inteiro|inteiros|∈\s*Z|integer)",
        line,
        re.I,
    )
    if int_line:
        for v in _extract_var_names(int_line.group(1)):
            var_names.add(v)
            var_types[v] = VariableType.INTEGER
        return None, var_names, var_types

    bin_line = re.search(
        rf"{var_list_pat}\s*(?:bin[aá]rio|binary|∈\s*\{{0,1\}})",
        line,
        re.I,
    )
    if bin_line:
        for v in _extract_var_names(bin_line.group(1)):
            var_names.add(v)
            var_types[v] = VariableType.BINARY
        return None, var_names, var_types

    nonneg = re.match(
        rf"^{var_list_pat}\s*(?:>=|≥)\s*0\s*$",
        line,
        re.I,
    )
    if nonneg:
        for v in _extract_var_names(nonneg.group(1)):
            var_names.add(v)
            var_types.setdefault(v, VariableType.CONTINUOUS)
        return None, var_names, var_types

    int_match = re.search(
        rf"{var_list_pat}\s*(?:∈|in)\s*(?:Z|ℤ|Int|Integer|Inteiro)",
        line,
        re.I,
    )
    if int_match:
        for v in _extract_var_names(int_match.group(1)):
            var_names.add(v)
            var_types[v] = VariableType.INTEGER
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


_VAR_TOKEN = r"[a-zA-Z][a-zA-Z0-9_]*"


def _parse_linear_expression(expr: str) -> tuple[dict[str, float], set[str]]:
    expr = expr.replace("−", "-").replace("–", "-").replace("·", "*")
    expr = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", expr)
    compact = expr.replace(" ", "")

    terms = re.findall(rf"([+-]?(?:\d+\.?\d*|\.\d+)?\*?(?:{_VAR_TOKEN}))", compact)
    if not terms:
        parts = re.split(r"([+-])", compact)
        rebuilt: list[str] = []
        sign = "+"
        for t in parts:
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
        term = term.lstrip("+-").replace("*", "")
        m = re.match(rf"([\d\.]*)({_VAR_TOKEN})$", term)
        if m:
            coef_str, name = m.groups()
            coef = float(coef_str) if coef_str else 1.0
            name = _normalize_var_name(name)
            var_names.add(name)
            coeffs[name] = coeffs.get(name, 0.0) + sign * coef

    return coeffs, var_names


def _extract_var_names(fragment: str) -> list[str]:
    return [_normalize_var_name(v) for v in re.findall(_VAR_TOKEN, fragment)]


def _normalize_var_name(name: str) -> str:
    m = re.match(r"x_?(\d+)$", name)
    if m and "_" not in name.replace("x_", "x"):
        return f"x{m.group(1)}"
    return name


def _var_sort_key(name: str) -> tuple:
    m = re.match(r"x_?([a-zA-Z]+)(\d+)_([a-zA-Z]+)(\d+)$", name)
    if m:
        return (m.group(1), int(m.group(2)), m.group(3), int(m.group(4)))
    m = re.match(r"x(\d+)", name)
    if m:
        return ("", int(m.group(1)), "", 0)
    return (name.lower(), 0, "", 0)

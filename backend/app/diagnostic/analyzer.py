from __future__ import annotations

from app.models.problem import ObjectiveSense, ProblemModel, VariableType


def diagnose(problem: ProblemModel) -> dict:
    category = problem.problem_category()
    category_labels = {
        "PL": "Programação Linear",
        "PLI": "Programação Linear Inteira",
        "PLIB": "Programação Linear Inteira Binária",
        "PLIM": "Programação Linear Inteira Mista",
    }

    var_types = [v.var_type.value for v in problem.variables]
    is_continuous = all(v.var_type == VariableType.CONTINUOUS for v in problem.variables)
    n_binary = sum(1 for v in problem.variables if v.var_type == VariableType.BINARY)
    n_integer = sum(1 for v in problem.variables if v.var_type == VariableType.INTEGER)

    applicable, not_applicable, demonstracao = _method_availability(problem, is_continuous)

    modeling_issues = _check_modeling(problem)

    return {
        "tipo_problema": category_labels.get(category, category),
        "categoria_codigo": category,
        "n_variaveis": problem.n_vars,
        "n_restricoes": problem.n_constraints,
        "objetivo": "Maximização" if problem.objective_sense == ObjectiveSense.MAX else "Minimização",
        "tipo_variaveis": _describe_var_types(is_continuous, n_integer, n_binary),
        "detalhe_variaveis": var_types,
        "metodos_disponiveis": applicable,
        "metodos_demonstracao": demonstracao,
        "metodos_nao_aplicaveis": not_applicable,
        "alertas_modelagem": modeling_issues,
    }


def _method_availability(
    problem: ProblemModel, is_continuous: bool
) -> tuple[list[str], list[str], list[str]]:
    n_vars = problem.n_vars
    applicable: list[str] = []
    not_applicable: list[str] = []
    demonstracao: list[str] = []

    if n_vars == 2 and is_continuous:
        applicable.append("Método Gráfico")
    if is_continuous:
        applicable.extend(["Simplex", "Dual Simplex", "Dualidade"])
    else:
        applicable.extend(
            [
                "Relaxação Linear",
                "Branch and Bound",
                "Branch and Cut",
                "Planos de Corte (Gomory)",
                "Simplex",
                "Dualidade",
            ]
        )

    applicable.extend(["Algoritmo Genético", "Metaheurísticas"])

    if is_continuous:
        demonstracao = [
            "Relaxação Linear",
            "Branch and Bound",
            "Branch and Cut",
            "Planos de Corte (Gomory)",
        ]
        not_applicable = []

    return applicable, not_applicable, demonstracao


def _describe_var_types(is_continuous: bool, n_integer: int, n_binary: int) -> str:
    if is_continuous:
        return "Contínuo"
    parts = []
    if n_integer:
        parts.append(f"{n_integer} inteira(s)")
    if n_binary:
        parts.append(f"{n_binary} binária(s)")
    return "Misto (" + ", ".join(parts) + ")" if parts else "Inteiro"


def _check_modeling(problem: ProblemModel) -> list[str]:
    issues: list[str] = []
    if not problem.constraints:
        issues.append("O modelo não possui restrições explícitas.")
    if all(c == 0.0 for c in problem.objective.values()):
        issues.append("A função objetivo possui todos os coeficientes iguais a zero.")
    for c in problem.constraints:
        if not c.coefficients:
            issues.append("Existe restrição sem coeficientes nas variáveis.")
    return issues

from __future__ import annotations

from app.diagnostic.analyzer import diagnose
from app.models.problem import ProblemModel
from app.parsers.input_parser import detect_input_format, parse_problem
from app.pedagogical.dual import build_dual
from app.pedagogical.formatter import interpret_problem, model_to_latex
from app.solvers.graphical import GraphicalSolver
from app.solvers.simplex import SimplexSolver
from app.solvers.vertex_lp import solve_by_vertices


_METHOD_ALIASES = {
    "metodo grafico": "Método Gráfico",
    "simplex": "Simplex",
    "dualidade": "Dualidade",
    "dual": "Dualidade",
}


def _normalize_method(method: str | None) -> str | None:
    if not method:
        return None
    key = method.strip().lower()
    return _METHOD_ALIASES.get(key, method.strip())


def solve_educational(text: str, method: str | None = None) -> dict:
    """Orquestrador v0.5 — gráfico, Simplex e dualidade."""
    method = _normalize_method(method)
    input_format = detect_input_format(text)
    problem = parse_problem(text)
    diagnostic = diagnose(problem)

    response = {
        "1_identificacao": {
            "formato_entrada": input_format,
            "diagnostico": diagnostic,
            "interpretacao": interpret_problem(problem),
        },
        "2_formulacao": {
            "latex": model_to_latex(problem),
            "modelo": problem.model_dump(),
        },
        "3_metodo_escolhido": _choose_method(problem, diagnostic, method),
        "4_resolucao": {},
        "5_tabelas_calculos": {},
        "6_interpretacao": {},
        "7_comparacao": {},
        "8_conclusao": {},
    }

    chosen = response["3_metodo_escolhido"]["metodo_principal"]
    primary_solution: dict | None = None
    primary_z: float | None = None

    if chosen == "Método Gráfico" and problem.n_vars == 2:
        g = GraphicalSolver(problem).solve()
        response["4_resolucao"]["grafico"] = {
            "passos": [_step_dict(s) for s in g.steps],
            "svg": g.feasible_region_svg,
        }
        response["5_tabelas_calculos"]["vertices"] = g.vertices
        primary_solution = g.solution
        primary_z = g.optimal_value

    elif chosen == "Dualidade":
        primary_solution, primary_z = _solve_lp_primal(problem, response, papel="primal")

    elif chosen == "Simplex" or problem.n_vars != 2:
        primary_solution, primary_z = _solve_lp_primal(problem, response)

    else:
        g = GraphicalSolver(problem).solve()
        response["4_resolucao"]["grafico"] = {
            "passos": [_step_dict(s) for s in g.steps],
            "svg": g.feasible_region_svg,
        }
        primary_solution = g.solution
        primary_z = g.optimal_value

    response["4_resolucao"]["dualidade"] = build_dual(
        problem,
        primal_solution=primary_solution,
        primal_z=primary_z,
    )

    response["6_interpretacao"]["solucao"] = {
        "variaveis": primary_solution or {},
        "valor_objetivo": primary_z,
    }
    response["8_conclusao"]["resultado"] = (
        f"Z* = {primary_z:.6g}" if primary_z is not None else "Sem solução"
    )
    response["8_conclusao"]["alertas"] = diagnostic.get("alertas_modelagem", [])
    response["8_conclusao"]["metodo_executado"] = chosen
    return response


def _solve_lp_primal(
    problem: ProblemModel,
    response: dict,
    papel: str | None = None,
) -> tuple[dict[str, float], float | None]:
    s = SimplexSolver(problem).solve()
    payload: dict = {
        "status": s.status,
        "passos": [_simplex_step_dict(st) for st in s.steps],
        "latex": s.latex_steps,
    }
    if papel:
        payload["papel"] = papel
    response["4_resolucao"]["simplex"] = payload

    if s.status == "optimal" and s.optimal_value is not None and s.solution:
        return s.solution, s.optimal_value

    vtx = solve_by_vertices(problem)
    if vtx:
        sol, z = vtx
        payload["status"] = "optimal"
        payload["fallback"] = "vertices"
        payload["nota"] = (
            "Simplex não convergiu; solução obtida por enumeração de vértices."
        )
        return sol, z

    return s.solution or {}, s.optimal_value


def _choose_method(problem: ProblemModel, diagnostic: dict, method: str | None) -> dict:
    if method and str(method).strip():
        principal = method
    elif problem.n_vars == 2 and not problem.has_integer_vars():
        principal = "Método Gráfico"
    else:
        principal = "Simplex"

    return {
        "metodo_solicitado": method,
        "metodo_principal": principal,
        "metodos_disponiveis": diagnostic["metodos_disponiveis"],
        "metodos_demonstracao": diagnostic.get("metodos_demonstracao", []),
        "metodos_nao_aplicaveis": diagnostic["metodos_nao_aplicaveis"],
        "justificativa": _method_justification(problem, principal),
    }


def _method_justification(problem: ProblemModel, method: str) -> str:
    if method == "Método Gráfico":
        return "Duas variáveis contínuas permitem visualização geométrica da região factível."
    if method == "Simplex":
        return "Problema linear; Simplex percorre vértices da região factível."
    if method == "Dualidade":
        return (
            "Constrói o dual a partir do primal, resolve ambos (Simplex) "
            "e verifica dualidade forte (Z* primal = Z* dual)."
        )
    return f"Método {method} selecionado."


def _simplex_step_dict(st) -> dict:
    return {
        "iteracao": st.iteration,
        "descricao": st.description,
        "tabela": st.table,
        "tabela_antes": st.table_before,
        "base": st.basis,
        "fase": st.phase,
        "entrante": st.entering,
        "sainte": st.leaving,
        "linha_pivo": st.pivot_row,
        "coluna_pivo_exibicao": st.pivot_col_display,
        "pivot": {
            "linha": st.pivot_row,
            "linha_nome": st.leaving,
            "coluna": st.pivot_col,
            "coluna_exibicao": st.pivot_col_display,
            "coluna_nome": st.pivot_col_name,
            "valor": st.pivot_value,
            "operacao_elementar": st.elementary_ops,
            "operacao_elementar_latex": st.elementary_ops_latex,
            "matriz_identidade_depois": st.identity_matrix,
            "coluna_identidade": st.identity_pivot_col,
        }
        if st.pivot_row is not None
        else None,
        "operacao_elementar_latex": st.elementary_ops_latex,
        "matriz_identidade": st.identity_matrix,
        "calculos": st.calculations,
        "leitura_tableau": st.leitura_tableau,
    }


def _step_dict(s) -> dict:
    return {"passo": s.step, "descricao": s.description, "calculos": s.calculations}

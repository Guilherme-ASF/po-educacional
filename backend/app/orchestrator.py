from __future__ import annotations

from app.diagnostic.analyzer import diagnose
from app.models.problem import ProblemModel, VariableType
from app.parsers.input_parser import detect_input_format, parse_problem
from app.pedagogical.dual import build_dual
from app.pedagogical.formatter import interpret_problem, model_to_latex
from app.solvers.branch_bound import BranchBoundSolver
from app.solvers.branch_cut import BranchCutSolver
from app.solvers.genetic import GeneticSolver
from app.solvers.graphical import GraphicalSolver
from app.solvers.simplex import SimplexSolver
from app.solvers.vertex_lp import solve_by_vertices


_METHOD_ALIASES = {
    "relaxacao linear": "Relaxação Linear",
    "branch and bound": "Branch and Bound",
    "branch and cut": "Branch and Cut",
    "planos de corte (gomory)": "Planos de Corte (Gomory)",
    "algoritmo genetico": "Algoritmo Genético",
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


def solve_educational(
    text: str,
    method: str | None = None,
    ga_params: dict | None = None,
) -> dict:
    """Orquestrador principal: parse → diagnóstico → resolução pedagógica."""
    method = _normalize_method(method)
    input_format = detect_input_format(text)
    problem = parse_problem(text)
    diagnostic = diagnose(problem)
    ga_params = ga_params or {}

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

    elif chosen == "Simplex":
        primary_solution, primary_z = _solve_lp_primal(problem, response)

    elif chosen == "Branch and Bound":
        primary_solution, primary_z = _run_branch_bound(problem, response)

    elif chosen == "Branch and Cut":
        primary_solution, primary_z = _run_branch_cut(problem, response)

    elif chosen in ("Relaxação Linear", "Planos de Corte (Gomory)"):
        primary_solution, primary_z = _run_relaxation(problem, response, chosen)

    elif chosen == "Algoritmo Genético":
        primary_solution, primary_z = _run_genetic(problem, response, ga_params, set_primary=True)

    elif chosen == "Dualidade":
        primary_solution, primary_z = _solve_lp_primal(
            problem, response, papel="primal"
        )

    else:
        if problem.n_vars == 2 and not problem.has_integer_vars() and chosen != "Simplex":
            g = GraphicalSolver(problem).solve()
            response["4_resolucao"]["grafico"] = {
                "passos": [_step_dict(s) for s in g.steps],
                "svg": g.feasible_region_svg,
            }
            primary_solution = g.solution
            primary_z = g.optimal_value
        else:
            primary_solution, primary_z = _solve_lp_primal(problem, response)

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
    """Resolve PL primal: Simplex e, se necessário, enumeração de vértices."""
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


def _run_relaxation(problem: ProblemModel, response: dict, label: str) -> tuple[dict, float | None]:
    relaxed = problem.model_copy(deep=True)
    for v in relaxed.variables:
        v.var_type = VariableType.CONTINUOUS

    s = SimplexSolver(relaxed).solve()
    analysis = []
    for v in problem.variables:
        if v.var_type != VariableType.CONTINUOUS:
            val = s.solution.get(v.name, 0)
            if abs(val - round(val)) > 1e-6:
                analysis.append(
                    f"{v.name} = {val:.4g} — fracionário; aplicar Branch and Bound."
                )
            else:
                analysis.append(f"{v.name} = {val:.4g} — inteiro ✓")
        else:
            analysis.append(f"{v.name} = {s.solution.get(v.name, 0):.4g} (contínua)")

    if not problem.has_integer_vars():
        analysis.insert(
            0,
            "Problema já é PL contínuo: a relaxação linear coincide com o modelo original.",
        )

    response["4_resolucao"]["relaxacao_linear"] = {
        "passos_simplex": [_simplex_step_dict(st) for st in s.steps],
        "solucao": s.solution,
        "z": s.optimal_value,
        "analise_integralidade": analysis,
    }

    if label == "Planos de Corte (Gomory)" and problem.has_integer_vars():
        bc = BranchCutSolver(problem).solve()
        response["4_resolucao"]["gomory"] = {
            "passos": bc.steps,
            "cortes": [_cut_to_dict(c) for c in bc.cuts],
        }
        return bc.solution, bc.optimal_value

    return s.solution, s.optimal_value


def _run_branch_bound(problem: ProblemModel, response: dict) -> tuple[dict, float | None]:
    if not problem.has_integer_vars():
        relaxed = problem.model_copy(deep=True)
        s = SimplexSolver(relaxed).solve()
        response["4_resolucao"]["branch_and_bound"] = {
            "modo": "demonstracao_pl",
            "explicacao": (
                "Em PL contínuo não há ramificação: a solução do relaxamento já é ótima "
                "e integral (variáveis contínuas)."
            ),
            "relaxacao": {"solucao": s.solution, "z": s.optimal_value},
            "arvore": "Nó 0\n└── Solução contínua ótima (sem ramificações)",
            "passos": [
                {
                    "titulo": "Nó 0 — Relaxação linear",
                    "descricao": f"x1={s.solution.get('x1', 0):.4g}, x2={s.solution.get('x2', 0):.4g}, Z={s.optimal_value:.4g}",
                },
                {
                    "titulo": "Conclusão",
                    "descricao": "Nenhuma variável inteira a ramificar. B&B reduz-se ao Simplex.",
                },
            ],
        }
        return s.solution, s.optimal_value

    bb = BranchBoundSolver(problem).solve()
    response["4_resolucao"]["relaxacao_linear"] = bb.relaxation_first
    response["4_resolucao"]["branch_and_bound"] = {
        "passos": bb.steps,
        "arvore": bb.tree_ascii,
        "nos": [_node_to_dict(n) for n in bb.nodes],
    }
    response["5_tabelas_calculos"]["branch_bound"] = bb.steps
    return bb.solution, bb.optimal_value


def _run_branch_cut(problem: ProblemModel, response: dict) -> tuple[dict, float | None]:
    if not problem.has_integer_vars():
        s = SimplexSolver(problem).solve()
        response["4_resolucao"]["branch_and_cut"] = {
            "modo": "demonstracao_pl",
            "explicacao": (
                "Cortes de Gomory aplicam-se a variáveis inteiras. "
                "Em PL contínuo, o Simplex já resolve diretamente."
            ),
            "relaxacao_inicial": {"solucao": s.solution, "z": s.optimal_value},
            "cortes": [],
            "passos": [
                {
                    "titulo": "Relaxação inicial",
                    "descricao": f"Solução contínua ótima Z* = {s.optimal_value:.4g}",
                },
                {
                    "titulo": "Cortes",
                    "descricao": "Nenhum corte necessário — solução já satisfaz continuidade.",
                },
            ],
        }
        return s.solution, s.optimal_value

    bc = BranchCutSolver(problem).solve()
    response["4_resolucao"]["branch_and_cut"] = {
        "passos": bc.steps,
        "cortes": [_cut_to_dict(c) for c in bc.cuts],
    }
    return bc.solution, bc.optimal_value


def _run_genetic(
    problem: ProblemModel,
    response: dict,
    ga_params: dict,
    set_primary: bool,
) -> tuple[dict, float | None]:
    ga = GeneticSolver(
        problem,
        population_size=int(ga_params.get("populacao", 10)),
        max_generations=int(ga_params.get("geracoes", 20)),
        mutation_rate=float(ga_params.get("mutacao", 0.1)),
        crossover_rate=float(ga_params.get("cruzamento", 0.8)),
        seed=int(ga_params.get("seed", 42)),
    ).solve()

    response["4_resolucao"]["algoritmo_genetico"] = {
        "parametros": {
            "populacao": ga_params.get("populacao", 10),
            "geracoes": ga_params.get("geracoes", 20),
            "mutacao": ga_params.get("mutacao", 0.1),
            "cruzamento": ga_params.get("cruzamento", 0.8),
        },
        "codificacao": ga.encoding,
        "geracoes": [_gen_to_dict(g) for g in ga.generations],
        "criterio_parada": ga.stop_reason,
        "melhor": {"solucao": ga.best_solution, "fitness": ga.best_fitness},
    }

    z = sum(
        problem.objective.get(v, 0) * ga.best_solution.get(v, 0) for v in problem.var_names
    )
    return (ga.best_solution, z) if set_primary else ({}, None)


def _choose_method(problem: ProblemModel, diagnostic: dict, method: str | None) -> dict:
    available = diagnostic["metodos_disponiveis"]
    demo = diagnostic.get("metodos_demonstracao", [])

    # Sempre respeitar a escolha explícita do usuário (não filtrar por "disponíveis")
    if method and str(method).strip():
        principal = method
    elif problem.has_integer_vars():
        principal = "Branch and Bound"
    elif problem.n_vars == 2:
        principal = "Método Gráfico"
    else:
        principal = "Simplex"

    return {
        "metodo_solicitado": method,
        "metodo_principal": principal,
        "metodos_disponiveis": available,
        "metodos_demonstracao": demo,
        "metodos_nao_aplicaveis": diagnostic["metodos_nao_aplicaveis"],
        "justificativa": _method_justification(problem, principal),
    }


def _method_justification(problem: ProblemModel, method: str) -> str:
    if method == "Método Gráfico":
        return "Duas variáveis contínuas permitem visualização geométrica da região factível."
    if method == "Branch and Bound":
        if not problem.has_integer_vars():
            return "Modo demonstração: em PL contínuo a árvore tem um único nó (relaxação = ótimo)."
        return "Variáveis inteiras exigem enumeração via árvore de ramificação."
    if method == "Relaxação Linear":
        if not problem.has_integer_vars():
            return "O modelo já é contínuo; a relaxação coincide com o problema original."
        return "Primeiro passo em PLI: ignorar integridade e resolver como PL."
    if method == "Branch and Cut" or method == "Planos de Corte (Gomory)":
        return "Adiciona cortes para eliminar soluções fracionárias sem ramificar."
    if method == "Simplex":
        return "Problema linear; Simplex percorre vértices da região factível."
    if method == "Algoritmo Genético":
        return "Metaheurística; parâmetros configuráveis pelo usuário."
    if method == "Dualidade":
        return (
            "Constrói o dual a partir do primal, resolve ambos (Simplex) "
            "e verifica dualidade forte (Z* primal = Z* dual)."
        )
    return f"Método {method} selecionado."


def _method_comparison(problem: ProblemModel, diagnostic: dict) -> dict:
    comparisons = []
    if problem.n_vars == 2 and not problem.has_integer_vars():
        comparisons.append({
            "metodos": "Gráfico vs Simplex",
            "observacao": "Ambos encontram o mesmo ótimo global Z*=18 no exemplo clássico.",
        })
    if problem.has_integer_vars():
        comparisons.append({
            "metodos": "Branch and Bound vs Branch and Cut",
            "observacao": "B&B ramifica; B&C adiciona cortes de Gomory.",
        })
    comparisons.append({
        "metodos": "Exato vs Algoritmo Genético",
        "observacao": "Simplex garante otimalidade; GA é heurístico.",
    })
    return {"comparacoes": comparisons, "metodos_disponiveis": diagnostic["metodos_disponiveis"]}


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


def _node_to_dict(n) -> dict:
    return {
        "id": n.id,
        "pai": n.parent_id,
        "status": n.status,
        "poda": n.prune_reason,
        "z_relax": n.z_relax,
        "z_inteiro": n.z_integer,
        "ramificacao": {
            "variavel": n.branch_var,
            "direcao": n.branch_direction,
            "valor": n.branch_value,
        },
    }


def _cut_to_dict(c) -> dict:
    return {
        "iteracao": c.iteration,
        "variavel": c.violated_var,
        "fracionaria": c.fractional_value,
        "coeficientes": c.cut_coefficients,
        "rhs": c.cut_rhs,
        "calculos": c.calculations,
        "latex": c.latex,
    }


def _gen_to_dict(g) -> dict:
    return {
        "geracao": g.generation,
        "populacao": [
            {"cromossomo": ind.chromosome, "fitness": ind.fitness, "factivel": ind.feasible}
            for ind in g.population
        ],
        "melhor": {"cromossomo": g.best.chromosome, "fitness": g.best.fitness},
        "fitness_medio": g.avg_fitness,
        "operacoes": g.operations,
    }


def _executed_methods(response: dict) -> list[str]:
    methods = []
    r = response.get("4_resolucao", {})
    if "simplex" in r:
        methods.append("Simplex")
    if "grafico" in r:
        methods.append("Método Gráfico")
    if "relaxacao_linear" in r:
        methods.append("Relaxação Linear")
    if "branch_and_bound" in r:
        methods.append("Branch and Bound")
    if "branch_and_cut" in r or "gomory" in r:
        methods.append("Branch and Cut")
    if "algoritmo_genetico" in r:
        methods.append("Algoritmo Genético")
    if "dualidade" in r:
        methods.append("Dualidade")
    return methods

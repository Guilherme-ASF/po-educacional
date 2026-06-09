from __future__ import annotations

import time

from app.diagnostic.analyzer import diagnose
from app.models.problem import ProblemModel, VariableType
from app.parsers.input_parser import detect_input_format, parse_problem
from app.pedagogical.dual import build_dual
from app.pedagogical.formatter import interpret_problem, model_to_latex, model_to_text
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
            "texto": model_to_text(problem),
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


def solve_educational_model(
    problem: ProblemModel,
    method: str | None = None,
    ga_params: dict | None = None,
    mmol_meta: dict | None = None,
) -> dict:
    """Resolve um ProblemModel já montado (ex.: problemas MMOL)."""
    method = _normalize_method(method)
    diagnostic = diagnose(problem)
    ga_params = ga_params or {}

    if mmol_meta:
        diagnostic["mmol"] = mmol_meta

    response = {
        "1_identificacao": {
            "formato_entrada": "mmol" if mmol_meta else "modelo",
            "diagnostico": diagnostic,
            "interpretacao": interpret_problem(problem),
            "mmol": mmol_meta,
        },
        "2_formulacao": {
            "latex": model_to_latex(problem),
            "texto": model_to_text(problem),
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
        primary_solution, primary_z = _run_genetic(problem, response, ga_params, True)
    elif chosen == "Dualidade":
        primary_solution, primary_z = _solve_lp_primal(problem, response, "primal")
    else:
        primary_solution, primary_z = _run_branch_bound(problem, response)

    if not problem.has_integer_vars():
        response["4_resolucao"]["dualidade"] = build_dual(
            problem, primal_solution=primary_solution, primal_z=primary_z
        )

    response["6_interpretacao"]["solucao"] = {
        "variaveis": primary_solution or {},
        "valor_objetivo": primary_z,
    }
    response["8_conclusao"]["resultado"] = (
        f"Z* = {primary_z:.6g}" if primary_z is not None else "Sem solução"
    )
    response["8_conclusao"]["metodo_executado"] = chosen
    return response


def _wants_branch_bound_tree(metodo: str) -> bool:
    return metodo in (
        "Branch and Bound",
        "Branch and Cut",
        "Planos de Corte (Gomory)",
    )


def solve_mmol(
    chave: str,
    dados: dict | None = None,
    method: str | None = None,
    input_text: str | None = None,
) -> dict:
    from app.problems.registry import build_model, get_problem
    from app.parsers.input_parser import parse_problem

    meta = get_problem(chave)
    inst = dados if dados is not None else meta["instancia_padrao"]
    metodo = method or meta["metodo_sugerido"]
    mmol_meta = {
        "chave": chave,
        "id": meta["id"],
        "titulo": meta["titulo"],
        "tipo": meta["tipo"],
        "instancia": inst,
    }

    if input_text and input_text.strip():
        texto = input_text.strip()
        if chave == "1_multiprocessador":
            from app.problems.multiprocessor_text import extract_instance_from_text

            inst_edit = extract_instance_from_text(texto) or inst
            mmol_meta["instancia"] = inst_edit
            if _wants_branch_bound_tree(metodo):
                problem = parse_problem(texto)
                result = solve_educational_model(problem, metodo, mmol_meta=mmol_meta)
            else:
                problem = build_model(chave, inst_edit)
                result = _solve_mmol_dedicated(
                    chave, problem, meta, inst_edit, metodo, mmol_meta
                )
            result["2_formulacao"]["texto"] = texto
            result["mmol"] = mmol_meta
            return result

        problem = parse_problem(texto)
        result = solve_educational_model(problem, metodo, mmol_meta=mmol_meta)
        result["2_formulacao"]["texto"] = texto
        result["mmol"] = mmol_meta
        return result

    problem = build_model(chave, dados)

    dedicated = (
        "4_bin_packing",
        "7_tsp",
        "9_cutting_stock",
        "10_timetabling",
    )
    use_bb_multiprocessor = (
        chave == "1_multiprocessador" and _wants_branch_bound_tree(metodo)
    )
    if chave in dedicated:
        result = _solve_mmol_dedicated(chave, problem, meta, inst, metodo, mmol_meta)
    elif use_bb_multiprocessor:
        result = solve_educational_model(problem, metodo, mmol_meta=mmol_meta)
        from app.problems.multiprocessor_text import multiprocessor_to_text

        result["2_formulacao"]["texto"] = multiprocessor_to_text(inst)
    elif chave == "1_multiprocessador":
        result = _solve_mmol_dedicated(chave, problem, meta, inst, metodo, mmol_meta)
    else:
        result = solve_educational_model(problem, metodo, mmol_meta=mmol_meta)

    result["mmol"] = mmol_meta
    return result


def _solve_mmol_dedicated(
    chave: str,
    problem: ProblemModel,
    meta: dict,
    inst: dict,
    metodo: str,
    mmol_meta: dict,
) -> dict:
    diagnostic = diagnose(problem)
    diagnostic["mmol"] = mmol_meta

    sol: dict[str, float] = {}
    z: float | None = None
    extra: dict = {}

    if chave == "1_multiprocessador":
        from app.problems.multiprocessor_solver import solve_multiprocessor_brute

        sol, z = solve_multiprocessor_brute(inst)
        extra = {"multiprocessador_exato": {"metodo": "enumeração", "makespan": z}}
        conclusao = f"Z* = {z:.6g} (makespan ótimo por enumeração)"
    elif chave == "4_bin_packing":
        from app.problems.bin_packing_solver import solve_bin_packing_exact

        sol, z = solve_bin_packing_exact(inst)
        extra = {"bin_packing": {"metodo": "FFD + busca exata em k", "bins": z}}
        conclusao = f"Z* = {z:.6g} (mínimo de bins — busca exata)"
    elif chave == "7_tsp":
        from app.problems.tsp_solver import solve_tsp_brute_force

        sol, z = solve_tsp_brute_force(inst["distancias"])
        extra = {"tsp_exato": {"metodo": "enumeração", "tour_cost": z}}
        conclusao = f"Z* = {z:.6g} (TSP exato por enumeração)"
    elif chave == "10_timetabling":
        from app.problems.timetabling_solver import solve_timetabling_brute

        sol, z = solve_timetabling_brute(inst)
        extra = {"timetabling": {"metodo": "enumeração de grades", "pontuacao": z}}
        conclusao = f"Z* = {z:.6g} (grade ótima por enumeração)"
    else:
        from app.problems.cutting_stock_solver import solve_cutting_stock_greedy

        sol, z = solve_cutting_stock_greedy(inst)
        extra = {"cutting_stock": {"metodo": "backtracking em padrões", "blocos": z}}
        conclusao = f"Z* = {z:.6g} (cutting stock — busca exata em padrões)"

    bb_note = (
        "Para instâncias maiores, use Branch and Bound pelo modelo PLI completo "
        f"({metodo})."
    )

    texto = model_to_text(problem)
    if chave == "1_multiprocessador":
        from app.problems.multiprocessor_text import multiprocessor_to_text

        texto = multiprocessor_to_text(inst)

    return {
        "1_identificacao": {
            "formato_entrada": "mmol",
            "diagnostico": diagnostic,
            "interpretacao": interpret_problem(problem),
            "mmol": mmol_meta,
        },
        "2_formulacao": {
            "latex": model_to_latex(problem),
            "texto": texto,
            "modelo": problem.model_dump(),
        },
        "3_metodo_escolhido": {
            "metodo_solicitado": metodo,
            "metodo_principal": metodo,
            "metodos_disponiveis": diagnostic["metodos_disponiveis"],
            "justificativa": f"Solver dedicado MMOL — {meta['titulo']}. {bb_note}",
        },
        "4_resolucao": {**extra, "nota": bb_note},
        "5_tabelas_calculos": {},
        "6_interpretacao": {"solucao": {"variaveis": sol, "valor_objetivo": z}},
        "7_comparacao": {},
        "8_conclusao": {"resultado": conclusao, "metodo_executado": metodo},
    }


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

    t0 = time.perf_counter()
    bb = BranchBoundSolver(problem).solve()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    nos_explorados = sum(
        1 for n in bb.nodes if n.relaxation is not None or n.prune_reason
    )
    response["4_resolucao"]["relaxacao_linear"] = bb.relaxation_first
    response["4_resolucao"]["branch_and_bound"] = {
        "passos": bb.steps,
        "arvore": bb.tree_ascii,
        "nos": [_node_to_dict(n, bb, problem) for n in bb.nodes],
        "no_otimo": bb.optimal_node_id,
        "incumbentes": bb.incumbent_node_ids,
        "desempenho": {
            "nos_explorados": nos_explorados,
            "nos_total": len(bb.nodes),
            "tempo_ms": round(elapsed_ms, 2),
        },
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
    bb = None
    if problem.n_vars <= 12:
        bb = BranchBoundSolver(problem, max_nodes=500).solve()
    response["4_resolucao"]["branch_and_cut"] = {
        "passos": bc.steps,
        "cortes": [_cut_to_dict(c) for c in bc.cuts],
        "nos": [_node_to_dict(n, bb, problem) for n in bb.nodes] if bb else [],
        "no_otimo": bb.optimal_node_id if bb else None,
        "incumbentes": bb.incumbent_node_ids if bb else [],
        "desempenho": {
            "nos_explorados": (
                sum(1 for n in bb.nodes if n.relaxation is not None or n.prune_reason)
                if bb
                else 0
            ),
            "nos_total": len(bb.nodes) if bb else 0,
            "cortes": len(bc.cuts),
        },
        "nota_arvore": (
            "Árvore de ramificação (B&B) exibida para visualização; "
            "a solução principal usa cortes de Gomory (B&C)."
        ),
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


def _node_to_dict(n, bb, problem: ProblemModel) -> dict:
    relax = n.relaxation or {}
    sol = relax.get("solution") or n.integer_solution or {}
    return {
        "id": n.id,
        "rotulo": f"PL_{n.id + 1}",
        "pai": n.parent_id,
        "status": n.status,
        "tipo_exibicao": _bb_node_tipo(n, bb, problem),
        "poda": n.prune_reason,
        "z_relax": n.z_relax,
        "z_inteiro": n.z_integer,
        "solucao": sol,
        "passos_simplex": relax.get("passos_simplex", []),
        "ramificacao": {
            "variavel": n.branch_var,
            "direcao": n.branch_direction,
            "valor": n.branch_value,
            "rotulo": _branch_label(n.branch_var, n.branch_direction, n.branch_value),
        },
    }


def _branch_label(var: str | None, direction: str | None, value: float | None) -> str | None:
    if not var or direction is None or value is None:
        return None
    op = "≤" if direction == "<=" else "≥"
    sub = var.replace("x", "x_") if var.startswith("x") else var
    val = int(value) if abs(value - round(value)) < 1e-6 else value
    return f"{sub} {op} {val}"


def _bb_node_tipo(n, bb, problem: ProblemModel) -> str:
    from app.models.problem import ObjectiveSense

    reason = (n.prune_reason or "").lower()
    if "inviabilidade" in reason or n.status == "infeasible":
        return "inviavel"
    if n.id == bb.optimal_node_id:
        return "otimo"
    if n.id in bb.incumbent_node_ids:
        return "incumbente"
    if n.prune_reason or n.status == "pruned":
        return "podado"

    sol: dict[str, float] = {}
    if n.integer_solution:
        sol = n.integer_solution
    elif n.relaxation:
        sol = n.relaxation.get("solution") or {}

    if n.status == "integer" or (sol and _is_integer_solution(sol, problem)):
        z_int = n.z_integer if n.z_integer is not None else n.z_relax
        if z_int is not None and bb.optimal_value is not None and n.id != bb.optimal_node_id:
            if problem.objective_sense == ObjectiveSense.MAX:
                if z_int < bb.optimal_value - 1e-6:
                    return "podado"
            elif z_int > bb.optimal_value + 1e-6:
                return "podado"
        return "viavel"

    if n.z_relax is not None:
        return "relaxacao"

    return "pendente"


def _is_integer_solution(sol: dict[str, float], problem: ProblemModel) -> bool:
    from app.models.problem import VariableType

    for v in problem.variables:
        if v.var_type not in (VariableType.INTEGER, VariableType.BINARY):
            continue
        val = sol.get(v.name, 0.0)
        if v.var_type == VariableType.BINARY:
            if val > 1e-6 and val < 1.0 - 1e-6:
                return False
        elif abs(val - round(val)) > 1e-5:
            return False
    return True


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

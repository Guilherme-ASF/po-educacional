from __future__ import annotations

from app.models.problem import Constraint, ObjectiveSense, ProblemModel, Variable
from app.solvers.simplex import SimplexSolver
from app.solvers.vertex_lp import solve_by_vertices


def build_dual(
    problem: ProblemModel,
    primal_solution: dict[str, float] | None = None,
    primal_z: float | None = None,
) -> dict:
    """Formulação dual, solução dual e classificação de dualidade forte/fraca."""
    dual_model, conversion_notes = _primal_to_dual_model(problem)
    dual_latex = _dual_to_latex(problem, dual_model, conversion_notes)

    dual_solution: dict[str, float] = {}
    dual_z: float | None = None
    dual_status = "nao_resolvido"
    dual_erro: str | None = None

    if dual_model.n_constraints > 0:
        try:
            result = SimplexSolver(dual_model).solve()
            if (
                result.status == "optimal"
                and result.optimal_value is not None
                and _solution_feasible(dual_model, result.solution)
            ):
                dual_solution = _display_dual_solution(
                    problem, dual_model, result.solution
                )
                dual_z = result.optimal_value
                dual_status = "otimo"
            elif result.status == "unbounded":
                dual_status = "ilimitado"
                dual_erro = (
                    "Problema dual ilimitado (equivalente a primal inviável ou não limitado)."
                )
            else:
                dual_status = result.status
                dual_erro = f"Simplex retornou status: {result.status}"
        except Exception as exc:
            dual_status = "erro"
            dual_erro = str(exc)

        if dual_z is None:
            vtx = solve_by_vertices(dual_model)
            if vtx:
                dual_solution = _display_dual_solution(problem, dual_model, vtx[0])
                dual_z = vtx[1]
                dual_status = "otimo"
                dual_erro = None
            elif dual_status == "erro" or dual_status in ("optimal", "unbounded", "ilimitado"):
                dual_status = "inviavel"
                dual_erro = (
                    "Problema dual inviável — em geral o primal é ilimitado ou inviável."
                )

    if primal_z is None and primal_solution:
        primal_z = sum(
            problem.objective.get(v, 0) * primal_solution.get(v, 0)
            for v in problem.var_names
        )

    duality = _classify_duality(problem, primal_z, dual_z, dual_status)

    return {
        "primal": {
            "latex": _problem_to_latex(problem),
            "solucao": primal_solution or {},
            "z": primal_z,
        },
        "dual": {
            "latex": dual_latex,
            "modelo": dual_model.model_dump(),
            "sentido": dual_model.objective_sense.value,
            "variaveis": [v.name for v in dual_model.variables],
            "solucao": dual_solution,
            "z": dual_z,
            "status": dual_status,
            "erro": dual_erro,
            "notas_conversao": conversion_notes,
        },
        "dualidade": duality,
        "teoria": {
            "folga_complementar": (
                "x_j · (Σ a_ij y_i − c_j) = 0 e y_i · (b_i − Σ a_ij x_j) = 0. "
                "Restrição com folga ⇒ variável dual nula; variável primal nula ⇒ "
                "restrição dual saturada."
            ),
            "interpretacao_economica": (
                "y_i é o preço sombra do recurso i: quanto Z* melhora por unidade "
                "extra na restrição i."
            ),
        },
    }


def _display_dual_solution(
    primal: ProblemModel,
    dual_model: ProblemModel,
    raw: dict[str, float],
) -> dict[str, float]:
    """Converte y_i' → y_i quando houve substituição y_i = −y_i'."""
    out: dict[str, float] = {}
    is_max = primal.objective_sense == ObjectiveSense.MAX
    for i in range(primal.n_constraints):
        y = f"y{i + 1}"
        bar = f"{y}_bar"
        if bar in raw:
            sign = _dual_multiplier_sign(primal.constraints[i].sense, is_max)
            out[y] = -raw[bar] if sign == "nonpos" else raw[bar]
        elif y in raw:
            out[y] = raw[y]
    if not out:
        return dict(raw)
    return out


def _dual_multiplier_sign(primal_sense: str, primal_is_max: bool) -> str:
    """Sinal do multiplicador dual y_i: nonneg (≥0), nonpos (≤0) ou free."""
    if primal_sense == "=":
        return "free"
    if primal_is_max:
        return "nonneg" if primal_sense == "<=" else "nonpos"
    return "nonpos" if primal_sense == "<=" else "nonneg"


def _primal_to_dual_model(problem: ProblemModel) -> tuple[ProblemModel, list[str]]:
    """
    Regras de dualidade (x ≥ 0):
    - Primal max → dual min, (A^T y)_j ≥ c_j; y_i ≥ 0 se restrição i é ≤; y_i ≤ 0 se i é ≥.
    - Primal min → dual max, (A^T y)_j ≤ c_j; y_i ≤ 0 se restrição i é ≤; y_i ≥ 0 se i é ≥.
    """
    is_max = problem.objective_sense == ObjectiveSense.MAX
    names = problem.var_names
    notes: list[str] = []

    if is_max:
        notes.append(
            "Primal de maximização: dual de minimização com (A^T y)_j ≥ c_j."
        )
        dual_cst_sense: str = ">="
    else:
        notes.append(
            "Primal de minimização: dual de maximização com (A^T y)_j ≤ c_j."
        )
        dual_cst_sense = "<="

    dual_constraints: list[Constraint] = []
    for j, xj in enumerate(names):
        coeffs: dict[str, float] = {}
        for i, cst in enumerate(problem.constraints):
            aij = cst.coefficients.get(xj, 0.0)
            if aij != 0:
                coeffs[f"y{i + 1}"] = aij
        cj = problem.objective.get(xj, 0.0)
        dual_constraints.append(
            Constraint(
                coefficients=coeffs,
                sense=dual_cst_sense,
                rhs=cj,
                name=f"dual_{xj}",
            )
        )

    dual_obj: dict[str, float] = {
        f"y{i + 1}": cst.rhs for i, cst in enumerate(problem.constraints)
    }

    multiplier_bounds: list[tuple[str, str]] = []
    for i, cst in enumerate(problem.constraints):
        sign = _dual_multiplier_sign(cst.sense, is_max)
        multiplier_bounds.append((f"y{i + 1}", sign))
        if sign == "nonneg":
            notes.append(f"y_{i + 1} ≥ 0 (restrição primal {i + 1} é {cst.sense}).")
        elif sign == "nonpos":
            notes.append(f"y_{i + 1} ≤ 0 (restrição primal {i + 1} é {cst.sense}).")
        else:
            notes.append(f"y_{i + 1} livre em sinal (restrição primal {i + 1} é =).")

    return _standardize_dual_for_simplex(
        dual_obj=dual_obj,
        dual_constraints=dual_constraints,
        multiplier_bounds=multiplier_bounds,
        primal_is_max=is_max,
        notes=notes,
    )


def _standardize_dual_for_simplex(
    dual_obj: dict[str, float],
    dual_constraints: list[Constraint],
    multiplier_bounds: list[tuple[str, str]],
    primal_is_max: bool,
    notes: list[str],
) -> tuple[ProblemModel, list[str]]:
    """
    Substitui y_i ≤ 0 por y_i = −y_i' (y_i' ≥ 0) para o Simplex.
    Variáveis y_i ≥ 0 permanecem com o mesmo nome.
    """
    subst: dict[str, tuple[str, float]] = {}
    variables: list[Variable] = []

    for y_name, bound in multiplier_bounds:
        if bound == "nonpos":
            new_name = f"{y_name}_bar"
            subst[y_name] = (new_name, -1.0)
            variables.append(Variable(name=new_name))
            notes.append(
                f"Para o Simplex: {y_name} ≤ 0 ⇒ {y_name} = −{new_name}, {new_name} ≥ 0."
            )
        elif bound == "nonneg":
            subst[y_name] = (y_name, 1.0)
            variables.append(Variable(name=y_name))
        else:
            pos = f"{y_name}_pos"
            neg = f"{y_name}_neg"
            subst[y_name] = ("free", pos, neg)
            variables.extend([Variable(name=pos), Variable(name=neg)])
            notes.append(
                f"Variável livre {y_name} = {pos} − {neg}, com {pos}, {neg} ≥ 0."
            )

    def map_coeffs(coeffs: dict[str, float]) -> dict[str, float]:
        out: dict[str, float] = {}
        for v, c in coeffs.items():
            if v not in subst:
                continue
            entry = subst[v]
            if entry[0] == "free":
                _, pos, neg = entry
                out[pos] = out.get(pos, 0.0) + c
                out[neg] = out.get(neg, 0.0) - c
            else:
                nv, mult = entry
                out[nv] = out.get(nv, 0.0) + c * mult
        return {k: v for k, v in out.items() if abs(v) > 1e-12}

    new_obj = map_coeffs(dual_obj)
    new_constraints = [
        Constraint(
            coefficients=map_coeffs(c.coefficients),
            sense=c.sense,
            rhs=c.rhs,
            name=c.name,
        )
        for c in dual_constraints
    ]

    dual_model = ProblemModel(
        objective_sense=ObjectiveSense.MIN if primal_is_max else ObjectiveSense.MAX,
        objective=new_obj,
        constraints=new_constraints,
        variables=variables,
    )
    notes.append(
        "Modelo acima é o dual equivalente com todas as variáveis ≥ 0 (pronto para Simplex)."
    )
    return dual_model, notes


def _classify_duality(
    problem: ProblemModel,
    primal_z: float | None,
    dual_z: float | None,
    dual_status: str,
) -> dict:
    eps = 1e-3
    ok_status = dual_status in ("otimo", "optimal")
    if primal_z is None or dual_z is None:
        tipo = "indefinida"
        if dual_status in ("ilimitado", "unbounded"):
            descricao = (
                "Dual ilimitado: o primal pode ser inviável ou não limitado (verifique o gráfico)."
            )
        elif dual_status == "erro":
            descricao = "Erro ao resolver o dual — veja a mensagem de status no painel."
        else:
            descricao = "Não foi possível obter ambos os valores ótimos para comparar."
    elif not ok_status:
        tipo = "fraca_ou_inexistente"
        descricao = (
            f"Problema dual com status '{dual_status}'. "
            "Dualidade forte exige primal e dual factíveis e limitados."
        )
    elif abs(primal_z - dual_z) <= eps:
        tipo = "forte"
        descricao = (
            f"Z* primal = {primal_z:.6g} e Z* dual = {dual_z:.6g} (diferença ≤ {eps}). "
            "Dualidade forte: ambos factíveis ⇒ valores ótimos coincidem."
        )
    else:
        tipo = "fraca"
        descricao = (
            f"Z* primal = {primal_z:.6g} ≠ Z* dual = {dual_z:.6g}. "
            "Gap de dualidade — verifique factibilidade ou forma do modelo."
        )

    return {
        "tipo": tipo,
        "rotulo": {
            "forte": "Dualidade forte",
            "fraca": "Dualidade fraca (gap)",
            "fraca_ou_inexistente": "Dualidade fraca / dual não ótimo",
            "indefinida": "Dualidade não verificada",
        }.get(tipo, tipo),
        "descricao": descricao,
        "z_primal": primal_z,
        "z_dual": dual_z,
        "diferenca": abs(primal_z - dual_z) if primal_z is not None and dual_z is not None else None,
    }


def _dual_to_latex(
    problem: ProblemModel,
    dual: ProblemModel,
    notes: list[str],
) -> str:
    """LaTeX do dual na forma com sinais corretos dos multiplicadores."""
    is_max = problem.objective_sense == ObjectiveSense.MAX
    sense = "\\min" if is_max else "\\max"
    obj_parts = []
    for i, cst in enumerate(problem.constraints):
        vn = f"y_{i + 1}"
        obj_parts.append(f"{_fmt_num(cst.rhs)}{vn}")
    obj = " + ".join(obj_parts).replace("+ -", "- ")

    lines = [f"{sense} \\; Z_D = {obj}", "\\text{sujeito a}"]
    dual_cst_op = "\\geq" if is_max else "\\leq"
    for j, xj in enumerate(problem.var_names):
        terms = []
        for i, cst in enumerate(problem.constraints):
            a = cst.coefficients.get(xj, 0.0)
            if a != 0:
                terms.append(f"{_fmt(a)}y_{i + 1}")
        lhs = " + ".join(terms).replace("+ -", "- ")
        cj = problem.objective.get(xj, 0.0)
        lines.append(f"{lhs} {dual_cst_op} {_fmt_num(cj)}")

    y_bounds = []
    for i, cst in enumerate(problem.constraints):
        sign = _dual_multiplier_sign(cst.sense, is_max)
        if sign == "nonneg":
            y_bounds.append(f"y_{i + 1} \\geq 0")
        elif sign == "nonpos":
            y_bounds.append(f"y_{i + 1} \\leq 0")
        else:
            y_bounds.append(f"y_{i + 1} \\text{{ livre}}")
    lines.append(", ".join(y_bounds))
    body = " \\\\ ".join(lines)
    return f"\\begin{{gathered}} {body} \\end{{gathered}}"


def _problem_to_latex(problem: ProblemModel) -> str:
    sense = "\\max" if problem.objective_sense == ObjectiveSense.MAX else "\\min"
    obj = " + ".join(
        f"{_fmt(coef)}{v.replace('x', 'x_')}"
        for v, coef in problem.objective.items()
        if coef != 0
    )
    lines = [f"{sense} \\; Z = {obj}", "\\text{sujeito a}"]
    for cst in problem.constraints:
        lhs = " + ".join(
            f"{_fmt(c)}{v.replace('x', 'x_')}"
            for v, c in cst.coefficients.items()
            if c != 0
        )
        op = {"<=": "\\leq", ">=": "\\geq", "=": "="}[cst.sense]
        lines.append(f"{lhs} {op} {_fmt_num(cst.rhs)}")
    nonneg = ", ".join(f"{v.replace('x', 'x_')} \\geq 0" for v in problem.var_names)
    lines.append(nonneg)
    body = " \\\\ ".join(lines)
    return f"\\begin{{gathered}} {body} \\end{{gathered}}"


def _solution_feasible(problem: ProblemModel, solution: dict[str, float]) -> bool:
    if not solution:
        return False
    eps = 1e-5
    for cst in problem.constraints:
        lhs = sum(cst.coefficients.get(v, 0.0) * solution.get(v, 0.0) for v in problem.var_names)
        if cst.sense == "<=" and lhs > cst.rhs + eps:
            return False
        if cst.sense == ">=" and lhs < cst.rhs - eps:
            return False
        if cst.sense == "=" and abs(lhs - cst.rhs) > eps:
            return False
    for v in problem.variables:
        if solution.get(v.name, 0.0) < -eps:
            return False
    return True


def _fmt(val: float) -> str:
    """Coeficiente em termos (omite 1)."""
    if val == int(val):
        iv = int(val)
        if iv == 1:
            return ""
        if iv == -1:
            return "-"
        return str(iv)
    return f"{val:g}"


def _fmt_num(val: float) -> str:
    """Valor numérico completo (RHS, objetivo)."""
    if val == int(val):
        return str(int(val))
    return f"{val:g}"

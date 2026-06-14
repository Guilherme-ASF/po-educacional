from __future__ import annotations

from app.models.problem import ProblemModel
from app.solvers.simplex import SimplexStep


def simplex_steps_to_dict(steps: list[SimplexStep]) -> list[dict]:
    return [simplex_step_dict(st) for st in steps]


def simplex_step_dict(st: SimplexStep) -> dict:
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


def lp_solution_step_dict(
    sol: dict[str, float],
    z: float,
    problem: ProblemModel,
    *,
    solver: str = "scipy linprog",
) -> dict:
    """Passo pedagógico quando o Simplex não percorre o tableau (ex.: modelos com M)."""
    names = list(problem.var_names)
    active = sorted(
        (name, float(sol.get(name, 0.0)))
        for name in names
        if abs(sol.get(name, 0.0)) > 1e-9
    )
    inactive = [name for name in names if abs(sol.get(name, 0.0)) <= 1e-9]

    calculos = [f"{name} = {val:.6g}" for name, val in active]
    calculos.append(f"Z* = {z:.6g}")
    if len(active) > 24:
        calculos.append(f"(+ {len(active) - 24} variáveis não nulas omitidas na lista)")

    basis = [name for name, _ in active]
    tabela = _build_lp_solution_tableau(names, active, z)

    vars_basicas = [
        {
            "variavel": name,
            "valor": val,
            "coluna_B": val,
            "texto": f"Linha {name}: coluna B = {val:.6g} ⇒ {name} = {val:.6g}",
        }
        for name, val in active[:24]
    ]
    vars_nao_basicas = [
        {
            "variavel": name,
            "valor": 0.0,
            "texto": f"{name} fora da base ⇒ {name} = 0",
        }
        for name in inactive[:40]
    ]
    if len(inactive) > 40:
        vars_nao_basicas.append({
            "variavel": "…",
            "valor": 0.0,
            "texto": f"(+ {len(inactive) - 40} variáveis fora da base)",
        })

    obj_terms = " + ".join(
        f"{problem.objective.get(v, 0):.6g}·{sol.get(v, 0.0):.6g}"
        for v in names
        if abs(problem.objective.get(v, 0)) > 1e-12
    )

    return {
        "iteracao": 1,
        "descricao": f"Solução ótima da relaxação LP ({solver})",
        "tabela": tabela,
        "base": basis,
        "calculos": calculos,
        "leitura_tableau": {
            "variaveis_basicas": vars_basicas,
            "variaveis_nao_basicas": vars_nao_basicas,
            "z_ótimo": z,
            "calculo_Z": f"Z* = {obj_terms} = {z:.6g}" if obj_terms else f"Z* = {z:.6g}",
            "explicacao": [
                "Tableau final da relaxação linear (solução numérica do subproblema).",
                "Cada linha da base tem 1 na coluna da variável e o valor na coluna B.",
                "Variáveis fora da base (coeficientes 0 nas linhas) valem 0.",
            ],
        },
    }


def _fmt_num(val: float) -> str:
    if abs(val - round(val)) < 1e-6:
        return str(int(round(val)))
    return f"{val:.6g}"


def _build_lp_solution_tableau(
    names: list[str],
    active: list[tuple[str, float]],
    z: float,
) -> list[list[str]]:
    """Tableau didático: linhas da base com valor na coluna B e linha Z."""
    header = [""] + names + ["B"]
    rows: list[list[str]] = [header]
    for bname, bval in active:
        rows.append(
            [bname]
            + ["1" if n == bname else "0" for n in names]
            + [_fmt_num(bval)]
        )
    rows.append(["Z"] + ["0"] * len(names) + [_fmt_num(z)])
    return rows

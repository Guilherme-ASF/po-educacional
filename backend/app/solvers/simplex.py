from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.models.problem import ObjectiveSense, ProblemModel
from app.solvers.fractions_util import frac_div_str, frac_str, matrix_to_frac_str

@dataclass
class SimplexStep:
    iteration: int
    description: str
    table: list[list[str]]
    basis: list[str]
    phase: int = 2
    entering: str | None = None
    leaving: str | None = None
    pivot: tuple[int, int] | None = None
    table_before: list[list[str]] | None = None
    pivot_row: int | None = None
    pivot_col: int | None = None
    pivot_col_name: str | None = None
    pivot_value: float | None = None
    elementary_ops: list[str] = field(default_factory=list)
    elementary_ops_latex: list[str] = field(default_factory=list)
    pivot_col_display: int | None = None
    calculations: list[str] = field(default_factory=list)
    leitura_tableau: dict | None = None
    razoes: list[dict] = field(default_factory=list)
    identity_matrix: list[list[str]] | None = None
    identity_pivot_col: int | None = None


@dataclass
class SimplexResult:
    status: str
    optimal_value: float | None
    solution: dict[str, float]
    steps: list[SimplexStep]
    latex_steps: list[str]


class SimplexSolver:
    """
    Simplex no formato universitário:
    - Folgas/excesso: x_{n+1}, x_{n+2}, ... (mesma lógica de x1, x2, x3)
    - Colunas: x1, x2, ..., x_m, B
    - Linhas: variáveis da base (ex.: x3, x4) e Z
    """

    def __init__(self, problem: ProblemModel):
        self.problem = problem
        self.decision_names = list(problem.var_names)
        self.n_dec = len(self.decision_names)
        self.sense = problem.objective_sense

    def solve(self) -> SimplexResult:
        built = self._build_tableau()
        steps: list[SimplexStep] = []
        latex: list[str] = []

        all_vars: list[str] = built["all_vars"]
        basis: list[str] = list(built["basis"])
        table = np.array(built["table"], dtype=float)
        self.display_vars = built["display_vars"]
        self.row_labels = built["row_labels"]
        m = len(basis)
        self.n_aux = m + 1  # restrições + linha Z (ex.: 2 restrições → matriz 3×3)
        steps.append(
            SimplexStep(
                iteration=0,
                description="Tableau inicial — colunas x₁, x₂, folgas x₃, x₄, … e B.",
                table=_table_to_str(
                    table, all_vars, basis, self.display_vars, self.row_labels
                ),
                basis=list(basis),
                phase=2,
                calculations=built["notes"],
                identity_matrix=matrix_to_frac_str(np.eye(self.n_aux)),
            )
        )

        table, basis, _, ok, p2 = self._run_phase(
            table, all_vars, basis, phase=2,
            artificial_cols=[], artificial_names=[],
        )
        steps.extend(p2)

        if not ok:
            return SimplexResult("unbounded", None, {}, steps, latex)

        solution = {v: 0.0 for v in self.decision_names}
        full_values = {v: 0.0 for v in all_vars}
        for i, b in enumerate(basis):
            full_values[b] = float(table[i, -1])
        for v in self.decision_names:
            solution[v] = float(max(0.0, full_values.get(v, 0.0)))

        z_val = sum(
            self.problem.objective.get(v, 0) * solution.get(v, 0) for v in self.decision_names
        )

        correction_note: list[str] = []

        leitura = _build_tableau_reading(all_vars, basis, table, solution, z_val, self.decision_names, self.problem.objective)

        table_final = table.copy()
        if self.sense == ObjectiveSense.MAX and table_final[-1, -1] < 0:
            table_final[-1, -1] = z_val
        for j, v in enumerate(all_vars):
            if v not in basis:
                table_final[-1, j] = 0.0

        steps.append(
            SimplexStep(
                iteration=len(p2) + 1,
                description="Solução ótima — leitura pelo tableau (coluna B).",
                table=_table_to_str(
                    table_final, all_vars, basis, self.display_vars, self.row_labels
                ),
                basis=list(basis),
                phase=2,
                calculations=correction_note,
                leitura_tableau=leitura,
            )
        )

        return SimplexResult("optimal", z_val, solution, steps, latex)

    def _next_var_name(self, index: int) -> str:
        return f"x{index}"

    def _build_tableau(self) -> dict:
        notes: list[str] = []
        n = self.n_dec
        next_idx = n + 1
        all_vars = list(self.decision_names)
        var_index = {name: i for i, name in enumerate(all_vars)}

        rows: list[list[float]] = []
        basis: list[str] = []
        row_labels: list[str] = []
        for i, cst in enumerate(self.problem.constraints):
            row = [0.0] * (len(all_vars) + 1)
            for v, coef in cst.coefficients.items():
                if v in var_index:
                    row[var_index[v]] = coef

            if cst.sense == "<=":
                slack = self._next_var_name(next_idx)
                next_idx += 1
                all_vars.append(slack)
                var_index[slack] = len(all_vars) - 1
                row = self._pad_row(row, len(all_vars))
                row[var_index[slack]] = 1.0
                basis.append(slack)
                row_labels.append(slack)
                notes.append(
                    f"Restrição {i + 1} (≤): adicionada folga {slack} → "
                    f"{_format_constraint(cst)} + {slack} = {cst.rhs}"
                )
            elif cst.sense == ">=":
                surplus = self._next_var_name(next_idx)
                next_idx += 1
                all_vars.append(surplus)
                var_index[surplus] = len(all_vars) - 1
                row = self._pad_row(row, len(all_vars))
                row[var_index[surplus]] = -1.0
                notes.append(
                    f"Restrição {i + 1} (≥): adicionado excesso {surplus} → "
                    f"{_format_constraint(cst)} − {surplus} = {cst.rhs}"
                )
                row_labels.append(surplus)
                basis.append(surplus)
            else:
                art = self._next_var_name(next_idx)
                next_idx += 1
                all_vars.append(art)
                var_index[art] = len(all_vars) - 1
                row = self._pad_row(row, len(all_vars))
                row[var_index[art]] = 1.0
                basis.append(art)
                row_labels.append(art)
                notes.append(f"Restrição {i + 1} (=): variável de folga {art}")

            row = self._pad_row(row, len(all_vars))
            row[-1] = cst.rhs
            rows.append(row)

        ncol = len(all_vars) + 1
        for ri in range(len(rows)):
            rows[ri] = self._pad_row(rows[ri], len(all_vars))

        # Linha Z: Max Z = c1·x1 + c2·x2 + … → coeficientes positivos, B = 0 (sem Fase I / x5)
        obj_row = [0.0] * ncol
        for v in self.decision_names:
            c = self.problem.objective.get(v, 0.0)
            obj_row[var_index[v]] = c if self.sense == ObjectiveSense.MAX else -c
        obj_row[-1] = 0.0
        rows.append(obj_row)

        return {
            "table": rows,
            "all_vars": all_vars,
            "display_vars": list(all_vars),
            "row_labels": row_labels,
            "basis": basis,
            "notes": notes,
        }

    def _pad_row(self, row: list[float], n_vars: int) -> list[float]:
        """Preserva coeficientes e move o RHS para a última coluna (B)."""
        out = [0.0] * (n_vars + 1)
        if not row:
            return out
        rhs = row[-1]
        for i in range(min(len(row) - 1, n_vars)):
            out[i] = row[i]
        out[-1] = rhs
        return out

    def _build_phase2_row(self, table: np.ndarray, all_vars: list[str], basis: list[str]) -> np.ndarray:
        ncol = table.shape[1]
        z = np.zeros(ncol)
        for j, v in enumerate(self.decision_names):
            if v in all_vars:
                z[all_vars.index(v)] = (
                    -self.problem.objective.get(v, 0.0)
                    if self.sense == ObjectiveSense.MAX
                    else self.problem.objective.get(v, 0.0)
                )
        for bi in range(len(basis)):
            if basis[bi] in all_vars:
                col = all_vars.index(basis[bi])
                coef = z[col]
                if abs(coef) > 1e-9:
                    z -= coef * table[bi]
        return z

    def _resolve_degeneracy(
        self, table: np.ndarray, all_vars: list[str], basis: list[str]
    ) -> tuple[np.ndarray, list[str], list, list[SimplexStep]]:
        steps: list[SimplexStep] = []
        is_max = self.sense == ObjectiveSense.MAX

        for _ in range(20):
            z_before = self._current_z(table, basis)
            obj = table[-1, :-1]
            dec_cols = [all_vars.index(v) for v in self.decision_names if v in all_vars]
            pivoted = False

            for idx in dec_cols:
                if is_max and obj[idx] <= 1e-9:
                    continue
                if not is_max and obj[idx] >= -1e-9:
                    continue
                col = table[:-1, idx]
                if not np.any(col > 1e-9):
                    continue
                ratios = np.where(col > 1e-9, table[:-1, -1] / col, np.inf)
                lrow = int(np.argmin(ratios))
                trial = _pivot(table.copy(), lrow, idx)
                new_basis = basis.copy()
                new_basis[lrow] = all_vars[idx]
                z_after = self._current_z(trial, new_basis)
                if (is_max and z_after > z_before + 1e-9) or (not is_max and z_after < z_before - 1e-9):
                    table = trial
                    basis = new_basis
                    table[-1] = self._build_phase2_row(table, all_vars, basis)
                    pivoted = True
                    break
            if not pivoted:
                break
            _, basis, _, ok, more = self._run_phase(
                table, all_vars, basis, phase=2, artificial_cols=[], artificial_names=[]
            )
            steps.extend(more)
            if not ok:
                break
        return table, basis, [], steps

    def _current_z(self, table: np.ndarray, basis: list[str]) -> float:
        sol = {v: 0.0 for v in self.decision_names}
        for i, b in enumerate(basis):
            if b in sol:
                sol[b] = float(max(0, table[i, -1]))
        return sum(self.problem.objective.get(v, 0) * sol.get(v, 0) for v in self.decision_names)

    def _phase1_complete(self, basis: list[str], table: np.ndarray, artificial_names: list[str]) -> bool:
        for b in basis:
            if b in artificial_names:
                row = basis.index(b)
                if abs(table[row, -1]) > 1e-7:
                    return False
        return True

    def _run_phase(
        self,
        table: np.ndarray,
        all_vars: list[str],
        basis: list[str],
        phase: int,
        artificial_cols: list[int],
        artificial_names: list[str],
    ) -> tuple[np.ndarray, list[str], list[str], bool, list[SimplexStep]]:
        steps: list[SimplexStep] = []
        is_max = self.sense == ObjectiveSense.MAX
        m = table.shape[0] - 1

        for iteration in range(100):
            obj = table[-1, :-1]

            if phase == 1:
                if self._phase1_complete(basis, table, artificial_names):
                    return table, basis, [], True, steps
                nb_cols = [
                    j for j in range(len(obj))
                    if all_vars[j] not in basis
                ]
                sub = [obj[j] for j in nb_cols]
                if not sub or min(sub) >= -1e-9:
                    return table, basis, [], False, steps
                idx = nb_cols[int(np.argmin(sub))]
            else:
                candidates = [
                    j for j in range(len(all_vars))
                    if all_vars[j] not in basis
                ]
                if not candidates:
                    return table, basis, [], True, steps
                improving = [
                    j for j in candidates
                    if (obj[j] > 1e-9 if is_max else obj[j] < -1e-9)
                ]
                if not improving:
                    return table, basis, [], True, steps
                dec_improving = [
                    j for j in improving if all_vars[j] in self.decision_names
                ]
                if dec_improving:
                    # Maior coeficiente em Z entre x1, x2, … (ex.: 2 e 3 → entra x2)
                    idx = (
                        max(
                            dec_improving,
                            key=lambda j: self.problem.objective.get(all_vars[j], 0.0),
                        )
                        if is_max
                        else min(
                            dec_improving,
                            key=lambda j: self.problem.objective.get(all_vars[j], 0.0),
                        )
                    )
                else:
                    idx = (
                        max(improving, key=lambda j: obj[j])
                        if is_max
                        else min(improving, key=lambda j: obj[j])
                    )

            entering = all_vars[idx]
            col = table[:-1, idx]
            valid = col > 1e-9
            if not np.any(valid):
                return table, basis, [], False, steps

            ratios_list: list[dict] = []
            ratios = np.full(m, np.inf)
            for i in range(m):
                if col[i] > 1e-9:
                    ratios[i] = table[i, -1] / col[i]
                    linha_nome = basis[i]
                    ratios_list.append({
                        "linha": linha_nome,
                        "calculo": (
                            f"θ = B({linha_nome}) / {entering}({frac_str(col[i])}) "
                            f"= {frac_div_str(table[i, -1], col[i])}"
                        ),
                        "valor": float(ratios[i]),
                    })

            lrow = int(np.argmin(ratios))
            leaving = basis[lrow]
            pv = table[lrow, idx]

            if is_max and phase == 2 and entering in self.decision_names:
                ent_msg = (
                    f"Coluna entrante: {entering} "
                    f"(maior coeficiente de Z entre {', '.join(self.decision_names)})."
                )
            else:
                ent_msg = f"Coluna entrante: {entering}"
            calcs = [
                ent_msg,
                f"Regra do pivô: dividir coluna {entering} pela coluna B (menor θ ≥ 0).",
                f"Pivô na linha {leaving}, coluna {entering} = {frac_str(pv)}",
            ]
            for r in ratios_list:
                calcs.append(r["calculo"])

            table_before = _table_to_str(
                table, all_vars, basis, self.display_vars, self.row_labels
            )
            row_names = list(basis)
            n_aux = self.n_aux
            table_pre = table.copy()
            elem_ops, elem_latex = _elementary_operations(
                table_pre,
                lrow,
                idx,
                row_names,
                all_vars,
                self.display_vars,
                n_aux,
            )
            E_step = _pivot_matrix(np.eye(n_aux, dtype=float), table_pre, lrow, idx)
            pivot_col_display = (
                self.display_vars.index(entering)
                if entering in self.display_vars
                else idx
            )

            table = _pivot(table, lrow, idx)
            basis[lrow] = entering

            steps.append(
                SimplexStep(
                    iteration=iteration + 1,
                    description=f"Iteração {iteration + 1}: {entering} entra, {leaving} sai",
                    table=_table_to_str(
                        table, all_vars, basis, self.display_vars, self.row_labels
                    ),
                    table_before=table_before,
                    basis=list(basis),
                    phase=phase,
                    entering=entering,
                    leaving=leaving,
                    pivot=(lrow, idx),
                    pivot_row=lrow,
                    pivot_col=idx,
                    pivot_col_display=pivot_col_display,
                    pivot_col_name=entering,
                    pivot_value=float(pv),
                    elementary_ops=elem_ops,
                    elementary_ops_latex=elem_latex,
                    calculations=calcs,
                    razoes=ratios_list,
                    identity_matrix=matrix_to_frac_str(E_step),
                    identity_pivot_col=lrow,
                )
            )

        return table, basis, [], False, steps


def _format_constraint(cst) -> str:
    terms = [f"{coef:g}{v}" for v, coef in cst.coefficients.items() if coef != 0]
    return " + ".join(terms).replace("+ -", "- ")


def _pivot_matrix(M: np.ndarray, T: np.ndarray, pr: int, pc: int) -> np.ndarray:
    """Mesmas operações elementares do pivô do tableau, aplicadas à matriz M."""
    out = M.copy()
    pv = T[pr, pc]
    out[pr] = out[pr] / pv
    for i in range(out.shape[0]):
        if i != pr:
            f = T[i, pc]
            if abs(f) > 1e-12:
                out[i] -= f * out[pr]
    return out


def _pivot(table: np.ndarray, pr: int, pc: int) -> np.ndarray:
    t = table.copy()
    pv = t[pr, pc]
    t[pr] /= pv
    for i in range(t.shape[0]):
        if i != pr:
            f = t[i, pc]
            if abs(f) > 1e-12:
                t[i] -= f * t[pr]
    return t


def _table_to_str(
    table: np.ndarray,
    all_vars: list[str],
    basis: list[str],
    display_vars: list[str] | None = None,
    row_labels: list[str] | None = None,
) -> list[list[str]]:
    """Formato faculdade: colunas x1…x_m, folgas, B | linhas = base + Z."""
    cols = display_vars if display_vars is not None else all_vars
    col_idx = [all_vars.index(v) for v in cols]
    header = [""] + cols + ["B"]
    rows = [header]
    for i, b in enumerate(basis):
        label = b
        rows.append(
            [label]
            + [frac_str(float(table[i, j])) for j in col_idx]
            + [frac_str(float(table[i, -1]))]
        )
    z_vals = [frac_str(float(table[-1, j])) for j in col_idx]
    rows.append(["Z"] + z_vals + [frac_str(float(table[-1, -1]))])
    return rows


def _build_tableau_reading(
    all_vars: list[str],
    basis: list[str],
    table: np.ndarray,
    solution: dict[str, float],
    z_val: float,
    decision_names: list[str],
    objective: dict[str, float],
) -> dict:
    b_col = -1
    basicas: list[dict] = []
    for i, b in enumerate(basis):
        val_b = float(table[i, b_col])
        basicas.append({
            "variavel": b,
            "valor": solution.get(b, val_b) if b in decision_names else val_b,
            "coluna_B": val_b,
            "texto": f"Linha {b}: coluna B = {val_b:.6g} ⇒ {b} = {val_b:.6g}",
        })

    nao_basicas = [
        {
            "variavel": v,
            "valor": solution.get(v, 0.0),
            "texto": f"{v} fora da base ⇒ {v} = {solution.get(v, 0.0):.6g}",
        }
        for v in decision_names
        if v not in basis
    ]

    obj_terms = " + ".join(
        f"{objective.get(v, 0):.6g}·{solution.get(v, 0.0):.6g}" for v in decision_names
    )

    return {
        "variaveis_basicas": basicas,
        "variaveis_nao_basicas": nao_basicas,
        "z_ótimo": z_val,
        "calculo_Z": f"Z* = {obj_terms} = {z_val:.6g}",
        "explicacao": [
            "Colunas: x₁, x₂, …, folgas x₃, x₄, …, e B (resultados).",
            "Linhas: variável da base (ex.: x₃, x₄) e linha Z.",
            "Valor de cada variável na base = número na coluna B da sua linha.",
            "Variáveis fora da base = 0.",
        ],
    }


def _row_vec_latex(row: np.ndarray, col_indices: list[int]) -> str:
    parts = [frac_str(float(row[j])) for j in col_indices] + [frac_str(float(row[-1]))]
    return r"\left(" + r",\; ".join(parts) + r"\right)"


def _elementary_operations(
    table: np.ndarray,
    pivot_row: int,
    pivot_col: int,
    row_names: list[str],
    all_vars: list[str],
    display_vars: list[str],
    n_aux: int,
) -> tuple[list[str], list[str]]:
    """Operações textuais + LaTeX no formato L_{xi}^{novo} = (…) ± … = (…)."""
    entering = all_vars[pivot_col]
    pr = pivot_row
    pv = float(table[pr, pivot_col])
    pv_s = frac_str(pv)
    labels = row_names + ["Z"]
    col_disp = [all_vars.index(v) for v in display_vars]

    new_pr = table[pr].copy() / pv
    old_pr = table[pr]

    text_ops = [
        f"Matriz elementar {n_aux}×{n_aux} deste pivô (restrições + Z).",
        f"Coluna entrante: {entering}; pivô = {pv_s} na linha {labels[pr]}.",
        f"Linha {labels[pr]} ← dividir pelo pivô {pv_s}.",
    ]
    latex_ops = [
        f"L_{{{labels[pr]}}}^{{\\text{{novo}}}} = {_row_vec_latex(old_pr, col_disp)}"
        f" \\div {pv_s} = {_row_vec_latex(new_pr, col_disp)}",
    ]

    for i in range(n_aux):
        if i == pr:
            continue
        fcoef = float(table[i, pivot_col])
        if abs(fcoef) < 1e-12:
            continue
        old_i = table[i]
        new_i = old_i - fcoef * new_pr
        sign_tex = "-" if fcoef > 0 else "+"
        sign_txt = "-" if fcoef > 0 else "+"
        mul = frac_str(abs(fcoef))
        scaled = fcoef * new_pr
        text_ops.append(
            f"Linha {labels[i]} ← Linha {labels[i]} {sign_txt} {mul}·Linha {labels[pr]}"
        )
        latex_ops.append(
            f"L_{{{labels[i]}}}^{{\\text{{novo}}}} = {_row_vec_latex(old_i, col_disp)}"
            f" {sign_tex} {mul} \\cdot {_row_vec_latex(new_pr, col_disp)}"
            f" = {_row_vec_latex(new_i, col_disp)}"
        )

    text_ops.append(f"Nova base: {entering} substitui {labels[pr]}.")
    return text_ops, latex_ops

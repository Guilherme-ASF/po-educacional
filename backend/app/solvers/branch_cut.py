from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.models.problem import ObjectiveSense, ProblemModel, VariableType
from app.solvers.simplex import SimplexSolver


@dataclass
class GomoryCut:
    iteration: int
    violated_var: str
    fractional_value: float
    cut_coefficients: dict[str, float]
    cut_rhs: float
    calculations: list[str]
    latex: str


@dataclass
class BranchCutResult:
    status: str
    optimal_value: float | None
    solution: dict[str, float]
    cuts: list[GomoryCut]
    steps: list[dict]
    simplex_iterations: int


class BranchCutSolver:
    """Branch and Cut pedagógico com cortes de Gomory para variáveis inteiras."""

    def __init__(self, problem: ProblemModel):
        self.problem = problem
        self.working = problem.model_copy(deep=True)
        for v in self.working.variables:
            v.var_type = VariableType.CONTINUOUS

    def solve(self, max_cuts: int = 10) -> BranchCutResult:
        cuts: list[GomoryCut] = []
        steps: list[dict] = []
        total_simplex = 0

        steps.append({
            "titulo": "Relaxação Inicial",
            "descricao": "Resolvemos o PL contínuo (relaxação linear).",
        })

        for iteration in range(max_cuts):
            result = SimplexSolver(self.working).solve()
            total_simplex += len(result.steps)

            if result.status != "optimal":
                return BranchCutResult(
                    status=result.status,
                    optimal_value=None,
                    solution={},
                    cuts=cuts,
                    steps=steps,
                    simplex_iterations=total_simplex,
                )

            sol = result.solution
            steps.append({
                "titulo": f"Iteração {iteration + 1} — Solução do relaxamento",
                "descricao": f"Z = {result.optimal_value:.4g}",
                "solucao": {k: round(v, 6) for k, v in sol.items()},
            })

            frac_var = None
            frac_val = 0.0
            for v in self.problem.variables:
                if v.var_type in (VariableType.INTEGER, VariableType.BINARY):
                    val = sol.get(v.name, 0)
                    if abs(val - round(val)) > 1e-6:
                        frac_var = v.name
                        frac_val = val
                        break

            if frac_var is None:
                steps.append({
                    "titulo": "Solução inteira encontrada",
                    "descricao": "Todas as variáveis inteiras assumem valores inteiros.",
                })
                return BranchCutResult(
                    status="optimal",
                    optimal_value=result.optimal_value,
                    solution=sol,
                    cuts=cuts,
                    steps=steps,
                    simplex_iterations=total_simplex,
                )

            f_val = frac_val - math.floor(frac_val)
            calcs = [
                f"Variável violada: {frac_var} = {frac_val:.6g}",
                f"Parte fracionária f = {frac_val:.6g} - ⌊{frac_val:.6g}⌋ = {f_val:.6g}",
            ]

            cut_coeffs: dict[str, float] = {}
            for vn in self.problem.var_names:
                coef = self.problem.objective.get(vn, 0)  # placeholder - simplified Gomory
                cut_coeffs[vn] = 0.0

            # Simplified Gomory cut: sum of fractional parts
            for vn in self.problem.var_names:
                s_val = sol.get(vn, 0)
                sf = s_val - math.floor(s_val)
                if sf > 1e-6:
                    cut_coeffs[vn] = sf / f_val if f_val > 1e-6 else sf

            cut_coeffs[frac_var] = cut_coeffs.get(frac_var, 0) + 1.0 / f_val if f_val > 1e-6 else 1
            cut_rhs = math.floor(frac_val) + f_val

            calcs.append("Corte de Gomory (forma pedagógica simplificada):")
            calcs.append(
                " + ".join(f"{c:.4g}·{v}" for v, c in cut_coeffs.items() if abs(c) > 1e-9)
                + f" ≤ {cut_rhs:.4g}"
            )

            latex = (
                "\\sum_j f_j x_j \\leq f_0 \\quad \\text{(corte de Gomory)}"
            )

            cut = GomoryCut(
                iteration=iteration + 1,
                violated_var=frac_var,
                fractional_value=f_val,
                cut_coefficients=cut_coeffs,
                cut_rhs=cut_rhs,
                calculations=calcs,
                latex=latex,
            )
            cuts.append(cut)

            from app.models.problem import Constraint

            self.working.constraints.append(
                Constraint(
                    coefficients=cut_coeffs,
                    sense="<=",
                    rhs=cut_rhs,
                    name=f"Gomory_{iteration + 1}",
                )
            )

            steps.append({
                "titulo": f"Detecção de violação — Corte {iteration + 1}",
                "descricao": f"a^T x > b violado por {frac_var} = {frac_val:.4g}",
                "calculos": calcs,
                "novo_modelo": f"Adicionada restrição de corte #{iteration + 1}",
            })

        return BranchCutResult(
            status="cut_limit",
            optimal_value=result.optimal_value,
            solution=sol,
            cuts=cuts,
            steps=steps,
            simplex_iterations=total_simplex,
        )

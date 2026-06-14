from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.models.problem import Constraint, ObjectiveSense, ProblemModel, VariableType
from app.solvers.serialize import lp_solution_step_dict, simplex_steps_to_dict
from app.solvers.simplex import SimplexSolver

_MAX_SIMPLEX_PEDAGOGY_VARS = 14


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
    reinforced_model: ProblemModel | None = None
    final_relaxation: dict | None = None


class BranchCutSolver:
    """Branch and Cut pedagógico com cortes de Gomory para variáveis inteiras."""

    def __init__(self, problem: ProblemModel):
        self.problem = problem
        self.working = problem.model_copy(deep=True)
        for v in self.working.variables:
            v.var_type = VariableType.CONTINUOUS

    def _reinforced_pli(self, cuts: list[GomoryCut]) -> ProblemModel:
        """PLI original com cortes de Gomory — base para a árvore B&C."""
        p = self.problem.model_copy(deep=True)
        for cut in cuts:
            p.constraints.append(
                Constraint(
                    coefficients=cut.cut_coefficients,
                    sense="<=",
                    rhs=cut.cut_rhs,
                    name=f"Gomory_{cut.iteration}",
                )
            )
        return p

    def _relaxation_passos(
        self, result, sol: dict[str, float], z: float
    ) -> list[dict]:
        if self.problem.n_vars <= _MAX_SIMPLEX_PEDAGOGY_VARS and result.steps:
            try:
                steps = simplex_steps_to_dict(result.steps)
                if steps:
                    return steps
            except Exception:
                pass
        return [lp_solution_step_dict(sol, z, self.working, solver="simplex")]

    def _solve_working_lp(self) -> tuple[str, dict[str, float], float | None, object | None]:
        """Relaxação LP: scipy (autoritativo) e Simplex pedagógico para tableau."""
        from app.solvers.lp_relaxation import solve_lp_relaxation

        sol: dict[str, float] | None = None
        z: float | None = None
        sx_result = None

        try:
            lp = solve_lp_relaxation(self.working)
            if lp is not None:
                sol, z = lp
        except Exception:
            pass

        if self.problem.n_vars <= _MAX_SIMPLEX_PEDAGOGY_VARS:
            try:
                sx = SimplexSolver(self.working).solve()
                sx_result = sx
                if sol is None and sx.status == "optimal" and sx.solution and sx.optimal_value is not None:
                    sol, z = sx.solution, float(sx.optimal_value)
            except Exception:
                pass

        if sol is None or z is None:
            if sx_result is not None and sx_result.status == "unbounded":
                return "unbounded", {}, None, sx_result
            return "infeasible", {}, None, sx_result

        return "optimal", sol, z, sx_result

    def solve(self, max_cuts: int = 10) -> BranchCutResult:
        cuts: list[GomoryCut] = []
        steps: list[dict] = []
        total_simplex = 0
        final_relaxation: dict | None = None

        steps.append({
            "titulo": "Relaxação Inicial",
            "descricao": "Resolvemos o PL contínuo (relaxação linear).",
        })

        for iteration in range(max_cuts):
            status, sol, z, sx_result = self._solve_working_lp()
            if sx_result is not None:
                total_simplex += len(sx_result.steps)

            if status != "optimal" or sol is None or z is None:
                return BranchCutResult(
                    status=status,
                    optimal_value=(
                        float(final_relaxation["z"])
                        if final_relaxation and final_relaxation.get("z") is not None
                        else None
                    ),
                    solution=(
                        dict(final_relaxation.get("solution") or {})
                        if final_relaxation
                        else {}
                    ),
                    cuts=cuts,
                    steps=steps + [{
                        "titulo": "Relaxação interrompida",
                        "descricao": (
                            f"Cortes de Gomory tornaram o relaxamento {status}. "
                            "A última relaxação factível é usada para exibição."
                        ),
                    }],
                    simplex_iterations=total_simplex,
                    reinforced_model=self._reinforced_pli(cuts) if cuts else None,
                    final_relaxation=final_relaxation,
                )

            passos = (
                self._relaxation_passos(sx_result, sol, z)
                if sx_result is not None
                else [lp_solution_step_dict(sol, z, self.working, solver="scipy linprog")]
            )
            final_relaxation = {
                "solution": sol,
                "z": z,
                "passos_simplex": passos,
            }
            steps.append({
                "titulo": f"Iteração {iteration + 1} — Solução do relaxamento",
                "descricao": f"Z = {z:.4g}",
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
                reinforced = self._reinforced_pli(cuts)
                return BranchCutResult(
                    status="optimal",
                    optimal_value=z,
                    solution=sol,
                    cuts=cuts,
                    steps=steps,
                    simplex_iterations=total_simplex,
                    reinforced_model=reinforced,
                    final_relaxation=final_relaxation,
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

        reinforced = self._reinforced_pli(cuts)
        return BranchCutResult(
            status="cut_limit",
            optimal_value=z,
            solution=sol,
            cuts=cuts,
            steps=steps,
            simplex_iterations=total_simplex,
            reinforced_model=reinforced,
            final_relaxation=final_relaxation,
        )

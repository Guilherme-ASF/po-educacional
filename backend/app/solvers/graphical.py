from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.models.problem import ObjectiveSense, ProblemModel


@dataclass
class GraphicalStep:
    step: int
    description: str
    calculations: list[str] = field(default_factory=list)


@dataclass
class GraphicalResult:
    status: str
    optimal_value: float | None
    solution: dict[str, float]
    steps: list[GraphicalStep]
    vertices: list[dict[str, float]]
    feasible_region_svg: str
    optimal_point: dict[str, float] | None


class GraphicalSolver:
    """Método gráfico para PL com 2 variáveis."""

    def __init__(self, problem: ProblemModel):
        if problem.n_vars != 2:
            raise ValueError("Método gráfico aplicável apenas a problemas com 2 variáveis.")
        self.problem = problem
        self.v1, self.v2 = problem.var_names

    def solve(self) -> GraphicalResult:
        steps: list[GraphicalStep] = []
        steps.append(
            GraphicalStep(
                step=1,
                description="Identificação das retas de fronteira de cada restrição.",
                calculations=self._boundary_lines(),
            )
        )

        vertices = self._find_vertices()
        steps.append(
            GraphicalStep(
                step=2,
                description=f"Interseções candidatas (vértices): {len(vertices)} ponto(s) encontrado(s).",
                calculations=[
                    f"Vértice {i + 1}: {self.v1}={v[self.v1]:.4g}, {self.v2}={v[self.v2]:.4g}"
                    for i, v in enumerate(vertices)
                ],
            )
        )

        feasible = [v for v in vertices if self._is_feasible(v)]
        steps.append(
            GraphicalStep(
                step=3,
                description=f"Vértices factíveis: {len(feasible)} de {len(vertices)}.",
                calculations=[
                    f"({v[self.v1]:.4g}, {v[self.v2]:.4g}) factível"
                    for v in feasible
                ],
            )
        )

        if not feasible:
            return GraphicalResult(
                status="infeasible",
                optimal_value=None,
                solution={},
                steps=steps,
                vertices=vertices,
                feasible_region_svg=self._render_svg(feasible, None),
                optimal_point=None,
            )

        if self._is_unbounded(feasible):
            steps.append(
                GraphicalStep(
                    step=4,
                    description="Problema ilimitado: Z pode crescer (max) ou decrescer (min) sem limite na região factível.",
                    calculations=[
                        "Existe direção factível que melhora a função objetivo indefinidamente "
                        "(ex.: aumentar x₁ mantendo x₂ = 0 nas restrições ≥)."
                    ],
                )
            )
            return GraphicalResult(
                status="unbounded",
                optimal_value=None,
                solution={},
                steps=steps,
                vertices=vertices,
                feasible_region_svg=self._render_svg(feasible, None),
                optimal_point=None,
            )

        evaluations = []
        best = None
        best_z = -np.inf if self.problem.objective_sense == ObjectiveSense.MAX else np.inf

        for v in feasible:
            z = sum(self.problem.objective.get(k, 0) * v[k] for k in [self.v1, self.v2])
            evaluations.append(f"Z({v[self.v1]:.4g}, {v[self.v2]:.4g}) = {z:.4g}")
            if self.problem.objective_sense == ObjectiveSense.MAX:
                if z > best_z:
                    best_z = z
                    best = v
            else:
                if z < best_z:
                    best_z = z
                    best = v

        steps.append(
            GraphicalStep(
                step=4,
                description="Avaliação de Z em cada vértice factível.",
                calculations=evaluations,
            )
        )
        steps.append(
            GraphicalStep(
                step=5,
                description=f"Solução ótima: {self.v1}={best[self.v1]:.4g}, {self.v2}={best[self.v2]:.4g}, Z*={best_z:.4g}",
                calculations=[
                    "O ótimo ocorre em um vértice da região factível (teorema fundamental da PL)."
                ],
            )
        )

        return GraphicalResult(
            status="optimal",
            optimal_value=float(best_z),
            solution=best,
            steps=steps,
            vertices=vertices,
            feasible_region_svg=self._render_svg(feasible, best),
            optimal_point=best,
        )

    def _boundary_lines(self) -> list[str]:
        """Interceptos da reta de fronteira zerando uma variável por vez."""
        lines = []
        for i, cst in enumerate(self.problem.constraints):
            a1 = cst.coefficients.get(self.v1, 0)
            a2 = cst.coefficients.get(self.v2, 0)
            b = cst.rhs
            lines.append(
                f"R{i + 1}: {_fmt(a1)}{self.v1} + {_fmt(a2)}{self.v2} {cst.sense} {_fmt(b)}"
            )
            lines.append(
                f"  Reta de fronteira: {_fmt(a1)}{self.v1} + {_fmt(a2)}{self.v2} = {_fmt(b)}"
            )
            intercepts: list[str] = []
            if abs(a2) > 1e-12:
                intercepts.append(f"{self.v2} = {_fmt(b / a2)}")
            if abs(a1) > 1e-12:
                intercepts.append(f"{self.v1} = {_fmt(b / a1)}")
            if intercepts:
                lines.append(f"  Zerando um termo: {' e '.join(intercepts)}")
            else:
                lines.append("  Restrição degenerada (sem reta de fronteira no plano).")
        return lines

    def _find_vertices(self) -> list[dict[str, float]]:
        lines: list[tuple[float, float, float]] = []
        for cst in self.problem.constraints:
            a1 = cst.coefficients.get(self.v1, 0)
            a2 = cst.coefficients.get(self.v2, 0)
            b = cst.rhs
            if cst.sense == ">=":
                a1, a2, b = -a1, -a2, -b
            elif cst.sense == "=":
                lines.append((a1, a2, b))
                lines.append((-a1, -a2, -b))
                continue
            lines.append((a1, a2, b))

        lines.append((1, 0, 0))
        lines.append((0, 1, 0))

        vertices: list[dict[str, float]] = []
        n = len(lines)
        for i in range(n):
            for j in range(i + 1, n):
                pt = _intersect(lines[i], lines[j])
                if pt:
                    vertices.append({self.v1: pt[0], self.v2: pt[1]})

        unique: list[dict[str, float]] = []
        for v in vertices:
            if not any(abs(v[self.v1] - u[self.v1]) < 1e-6 and abs(v[self.v2] - u[self.v2]) < 1e-6 for u in unique):
                unique.append(v)
        return unique

    def _is_unbounded(self, feasible: list[dict[str, float]]) -> bool:
        """Testa se ainda há melhoria factível em escala grande (2 variáveis)."""
        if not feasible:
            return False
        c1 = self.problem.objective.get(self.v1, 0.0)
        c2 = self.problem.objective.get(self.v2, 0.0)
        is_max = self.problem.objective_sense == ObjectiveSense.MAX
        base = max(
            feasible,
            key=lambda v: sum(self.problem.objective.get(k, 0) * v[k] for k in [self.v1, self.v2]),
        )
        z_base = sum(self.problem.objective.get(k, 0) * base[k] for k in [self.v1, self.v2])
        scale = 1e4
        directions = [
            (scale * (1 if c1 >= 0 else -1), 0.0),
            (0.0, scale * (1 if c2 >= 0 else -1)),
            (scale, scale * (c2 / c1 if c1 else 0)),
        ]
        for d1, d2 in directions:
            test = {self.v1: base[self.v1] + d1, self.v2: base[self.v2] + d2}
            if not self._is_feasible(test):
                continue
            z_test = sum(self.problem.objective.get(k, 0) * test[k] for k in [self.v1, self.v2])
            if is_max and z_test > z_base + 1e3:
                return True
            if not is_max and z_test < z_base - 1e3:
                return True
        return False

    def _is_feasible(self, v: dict[str, float]) -> bool:
        x1, x2 = v[self.v1], v[self.v2]
        if x1 < -1e-6 or x2 < -1e-6:
            return False
        for cst in self.problem.constraints:
            lhs = cst.coefficients.get(self.v1, 0) * x1 + cst.coefficients.get(self.v2, 0) * x2
            if cst.sense == "<=" and lhs > cst.rhs + 1e-6:
                return False
            if cst.sense == ">=" and lhs < cst.rhs - 1e-6:
                return False
            if cst.sense == "=" and abs(lhs - cst.rhs) > 1e-6:
                return False
        return True

    def _render_svg(
        self, feasible: list[dict[str, float]], optimal: dict[str, float] | None
    ) -> str:
        if not feasible:
            return "<svg width='400' height='400'><text x='20' y='200'>Região vazia</text></svg>"

        xs = [v[self.v1] for v in feasible]
        ys = [v[self.v2] for v in feasible]
        max_x = max(xs + [1]) * 1.2 + 1
        max_y = max(ys + [1]) * 1.2 + 1

        def tx(x: float) -> float:
            return 50 + (x / max_x) * 300

        def ty(y: float) -> float:
            return 350 - (y / max_y) * 300

        hull = _convex_hull([(v[self.v1], v[self.v2]) for v in feasible])
        points = " ".join(f"{tx(x)},{ty(y)}" for x, y in hull)

        svg = [
            f'<svg viewBox="0 0 420 400" xmlns="http://www.w3.org/2000/svg">',
            f'<rect width="420" height="400" fill="#f8fafc"/>',
            f'<polygon points="{points}" fill="rgba(59,130,246,0.2)" stroke="#3b82f6" stroke-width="2"/>',
        ]

        for cst in self.problem.constraints:
            a1 = cst.coefficients.get(self.v1, 0)
            a2 = cst.coefficients.get(self.v2, 0)
            if a2 != 0:
                x0, x1 = 0, max_x
                y0 = (cst.rhs - a1 * x0) / a2
                y1 = (cst.rhs - a1 * x1) / a2
                svg.append(
                    f'<line x1="{tx(x0)}" y1="{ty(y0)}" x2="{tx(x1)}" y2="{ty(y1)}" '
                    f'stroke="#94a3b8" stroke-width="1" stroke-dasharray="4"/>'
                )

        for v in feasible:
            svg.append(
                f'<circle cx="{tx(v[self.v1])}" cy="{ty(v[self.v2])}" r="4" fill="#64748b"/>'
            )

        if optimal:
            svg.append(
                f'<circle cx="{tx(optimal[self.v1])}" cy="{ty(optimal[self.v2])}" r="7" fill="#ef4444"/>'
            )
            svg.append(
                f'<text x="{tx(optimal[self.v1]) + 10}" y="{ty(optimal[self.v2])}" '
                f'font-size="12" fill="#ef4444">Ótimo</text>'
            )

        svg.append("</svg>")
        return "\n".join(svg)


def _intersect(l1: tuple[float, float, float], l2: tuple[float, float, float]) -> tuple[float, float] | None:
    a1, b1, c1 = l1
    a2, b2, c2 = l2
    det = a1 * b2 - a2 * b1
    if abs(det) < 1e-9:
        return None
    x = (c1 * b2 - c2 * b1) / det
    y = (a1 * c2 - a2 * c1) / det
    return x, y


def _convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    pts = sorted(set(points))
    if len(pts) <= 1:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _fmt(val: float) -> str:
    if val == int(val):
        return str(int(val))
    return f"{val:g}"

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from app.models.problem import Constraint, ObjectiveSense, ProblemModel, VariableType
from app.solvers.serialize import simplex_steps_to_dict
from app.solvers.simplex import SimplexSolver
from app.solvers.vertex_lp import solve_by_vertices


@dataclass
class BBNode:
    id: int
    parent_id: int | None
    depth: int
    branch_var: str | None = None
    branch_direction: str | None = None  # "<=" or ">="
    branch_value: float | None = None
    extra_constraints: list[dict] = field(default_factory=list)
    status: str = "pending"  # pending, active, pruned, integer, infeasible
    prune_reason: str | None = None
    relaxation: dict | None = None
    integer_solution: dict | None = None
    z_relax: float | None = None
    z_integer: float | None = None


@dataclass
class BranchBoundResult:
    status: str
    optimal_value: float | None
    solution: dict[str, float]
    nodes: list[BBNode]
    tree_ascii: str
    steps: list[dict]
    relaxation_first: dict
    optimal_node_id: int | None = None
    incumbent_node_ids: list[int] = field(default_factory=list)


class BranchBoundSolver:
    def __init__(self, problem: ProblemModel, max_nodes: int = 3000):
        self.original = problem
        self.max_nodes = max_nodes
        self.node_counter = 0
        self.nodes: list[BBNode] = []
        self.steps: list[dict] = []
        self.best_z: float | None = None
        self.best_sol: dict[str, float] | None = None
        self.incumbent_node_ids: list[int] = []
        self.upper_bound = float("inf") if problem.objective_sense == ObjectiveSense.MAX else float("-inf")

    def solve(self) -> BranchBoundResult:
        root = self._create_node(None, 0, [])
        self.steps.append({
            "titulo": "Passo 1 — Modelo Relaxado",
            "descricao": "Relaxamos x_i ∈ Z para x_i ∈ R e resolvemos por Simplex.",
        })

        relax_result = self._solve_node(root)
        self.relaxation_first = {
            "solucao": relax_result.get("solution", {}),
            "z": relax_result.get("z"),
            "analise_integralidade": self._integrality_analysis(relax_result.get("solution", {})),
        }

        if relax_result.get("status") == "infeasible":
            return BranchBoundResult(
                status="infeasible",
                optimal_value=None,
                solution={},
                nodes=self.nodes,
                tree_ascii=self._build_tree(),
                steps=self.steps,
                relaxation_first=self.relaxation_first,
            )

        queue = [root]
        seen_bounds: set[tuple] = {self._bounds_signature([])}
        explored = 0
        while queue:
            if explored >= self.max_nodes:
                self.steps.append({
                    "titulo": "Limite de nós atingido",
                    "descricao": f"Explorados {explored} nós (limite {self.max_nodes}).",
                })
                break
            explored += 1
            node = queue.pop(0)
            if node.status == "pruned":
                continue

            sig = self._bounds_signature(node.extra_constraints)
            if sig in seen_bounds and node.id != root.id:
                node.status = "pruned"
                node.prune_reason = "Subproblema já explorado"
                continue
            seen_bounds.add(sig)

            result = self._solve_node(node)
            if result["status"] == "infeasible":
                node.status = "pruned"
                node.prune_reason = "Poda por inviabilidade"
                self.steps.append({
                    "titulo": f"Nó {node.id} — Poda por inviabilidade",
                    "descricao": "O relaxamento linear deste subproblema não possui solução factível.",
                })
                continue

            sol = result["solution"]
            z = result["z"]
            node.relaxation = {
                "solution": sol,
                "z": z,
                "passos_simplex": result.get("passos_simplex", []),
            }
            node.z_relax = z

            if self._is_integer(sol):
                node.status = "integer"
                node.integer_solution = sol
                node.z_integer = z
                self.steps.append({
                    "titulo": f"Nó {node.id} — Solução inteira",
                    "descricao": f"Solução inteira encontrada: Z = {z:.4g}",
                    "solucao": sol,
                })
                if self._is_better(z):
                    self.best_z = z
                    self.best_sol = sol
                    self.incumbent_node_ids.append(node.id)
                    self._update_bound(z)
                continue

            # Bound pruning
            if not self._can_improve(z):
                node.status = "pruned"
                node.prune_reason = "Poda por dominância (limite)"
                self.steps.append({
                    "titulo": f"Nó {node.id} — Poda por dominância",
                    "descricao": f"Z_relax = {z:.4g} não melhora o incumbent Z* = {self.best_z}.",
                })
                continue

            branch_var, frac = self._choose_branch_var(sol)
            floor_v = int(frac // 1)
            ceil_v = floor_v + 1

            self.steps.append({
                "titulo": f"Nó {node.id} — Escolha da variável de ramificação",
                "descricao": (
                    f"Escolhendo {branch_var} = {sol[branch_var]:.4g}. "
                    f"Parte fracionária = {sol[branch_var] - floor_v:.4g}."
                ),
                "calculos": [
                    f"{branch_var} = {sol[branch_var]:.4g}",
                    f"⌊{branch_var}⌋ = {floor_v}, ⌈{branch_var}⌉ = {ceil_v}",
                ],
            })

            left_extra, left_infeas = self._consolidate_bounds(
                node.extra_constraints
                + [{"var": branch_var, "sense": "<=", "value": float(floor_v)}]
            )
            right_extra, right_infeas = self._consolidate_bounds(
                node.extra_constraints
                + [{"var": branch_var, "sense": ">=", "value": float(ceil_v)}]
            )

            created: list[str] = []
            for extras, infeas, direction, value in (
                (left_extra, left_infeas, "<=", floor_v),
                (right_extra, right_infeas, ">=", ceil_v),
            ):
                if infeas:
                    continue
                child_sig = self._bounds_signature(extras)
                if child_sig in seen_bounds:
                    continue
                child = self._create_node(
                    node.id, node.depth + 1, extras, branch_var, direction, value
                )
                created.append(f"Nó {child.id}: {branch_var} {direction} {value}")
                queue.append(child)

            self.steps.append({
                "titulo": f"Ramificação do Nó {node.id}",
                "descricao": (
                    f"Criados {', '.join(created)}"
                    if created
                    else "Nenhum subproblema novo."
                ),
            })

        return BranchBoundResult(
            status="optimal" if self.best_sol else "no_integer",
            optimal_value=self.best_z,
            solution=self.best_sol or {},
            nodes=self.nodes,
            tree_ascii=self._build_tree(),
            steps=self.steps,
            relaxation_first=self.relaxation_first,
            optimal_node_id=self._find_optimal_node_id(),
            incumbent_node_ids=list(self.incumbent_node_ids),
        )

    def _create_node(
        self,
        parent_id: int | None,
        depth: int,
        extras: list[dict],
        branch_var: str | None = None,
        direction: str | None = None,
        value: float | None = None,
    ) -> BBNode:
        self.node_counter += 1
        node = BBNode(
            id=self.node_counter - 1,
            parent_id=parent_id,
            depth=depth,
            branch_var=branch_var,
            branch_direction=direction,
            branch_value=value,
            extra_constraints=extras,
        )
        self.nodes.append(node)
        return node

    def _consolidate_bounds(
        self, extras: list[dict]
    ) -> tuple[list[dict], bool]:
        lowers: dict[str, float] = {}
        uppers: dict[str, float] = {}
        for ec in extras:
            v = ec["var"]
            if ec["sense"] == "<=":
                uppers[v] = min(uppers.get(v, float("inf")), ec["value"])
            else:
                lowers[v] = max(lowers.get(v, float("-inf")), ec["value"])
        for v in set(lowers) | set(uppers):
            if lowers.get(v, float("-inf")) > uppers.get(v, float("inf")) + 1e-9:
                return [], True
        consolidated: list[dict] = []
        for v, ub in uppers.items():
            consolidated.append({"var": v, "sense": "<=", "value": ub})
        for v, lb in lowers.items():
            consolidated.append({"var": v, "sense": ">=", "value": lb})
        return consolidated, False

    def _bounds_signature(self, extras: list[dict]) -> tuple:
        consolidated, infeasible = self._consolidate_bounds(extras)
        if infeasible:
            return ("infeasible",)
        return tuple(
            sorted((ec["var"], ec["sense"], ec["value"]) for ec in consolidated)
        )

    def _find_optimal_node_id(self) -> int | None:
        if self.best_z is None:
            return None
        for n in reversed(self.nodes):
            if n.z_integer is not None and abs(n.z_integer - self.best_z) < 1e-6:
                return n.id
        return None

    def _build_simplex_problem(self, node: BBNode) -> ProblemModel:
        """Mesmo subproblema do nó, com restrições >= convertidas para <= (Simplex)."""
        p = self._build_problem(node)
        converted: list[Constraint] = []
        for cst in p.constraints:
            if cst.sense == ">=":
                converted.append(
                    Constraint(
                        coefficients={k: -v for k, v in cst.coefficients.items()},
                        sense="<=",
                        rhs=-cst.rhs,
                        name=cst.name,
                    )
                )
            else:
                converted.append(cst)
        p.constraints = converted
        return p

    def _build_problem(self, node: BBNode) -> ProblemModel:
        p = copy.deepcopy(self.original)
        for ec in node.extra_constraints:
            p.constraints.append(
                Constraint(
                    coefficients={ec["var"]: 1.0},
                    sense=ec["sense"],
                    rhs=ec["value"],
                    name=f"BB_{ec['var']}_{ec['sense']}",
                )
            )
        for ov, v in zip(self.original.variables, p.variables):
            v.var_type = VariableType.CONTINUOUS
            if ov.var_type == VariableType.BINARY:
                p.constraints.append(
                    Constraint({v.name: 1.0}, "<=", 1.0, name=f"ub_{v.name}")
                )
        return p

    def _solve_node(self, node: BBNode) -> dict:
        from app.solvers.lp_relaxation import solve_lp_relaxation

        prob = self._build_problem(node)
        sx_prob = self._build_simplex_problem(node)
        passos_simplex: list[dict] = []

        try:
            lp = solve_lp_relaxation(prob)
            if lp is not None:
                sol, z = lp
                return {
                    "status": "optimal",
                    "solution": sol,
                    "z": z,
                    "passos_simplex": passos_simplex,
                }
        except Exception:
            pass

        try:
            sx = SimplexSolver(sx_prob).solve()
            if sx.status == "optimal":
                passos_simplex = simplex_steps_to_dict(sx.steps)
        except Exception:
            pass

        try:
            if prob.n_vars <= 8:
                vertex = solve_by_vertices(prob)
                if vertex is not None:
                    sol, z = vertex
                    return {
                        "status": "optimal",
                        "solution": sol,
                        "z": z,
                        "passos_simplex": passos_simplex,
                    }
        except Exception:
            pass

        try:
            sx = SimplexSolver(sx_prob).solve()
            if sx.status == "optimal" and sx.optimal_value is not None:
                if not passos_simplex:
                    passos_simplex = simplex_steps_to_dict(sx.steps)
                return {
                    "status": "optimal",
                    "solution": sx.solution,
                    "z": sx.optimal_value,
                    "passos_simplex": passos_simplex,
                }
        except Exception:
            pass
        return {"status": "infeasible", "passos_simplex": passos_simplex}

    def _integrality_analysis(self, sol: dict[str, float]) -> list[str]:
        lines = []
        for v in self.original.variables:
            if v.var_type in (VariableType.INTEGER, VariableType.BINARY):
                val = sol.get(v.name, 0)
                if abs(val - round(val)) > 1e-6:
                    lines.append(f"{v.name} = {val:.4g} — não é inteiro. Necessário Branch and Bound.")
                else:
                    lines.append(f"{v.name} = {val:.4g} — inteiro ✓")
        return lines

    def _is_integer(self, sol: dict[str, float]) -> bool:
        for v in self.original.variables:
            val = sol.get(v.name, 0)
            if v.var_type == VariableType.BINARY:
                if val > 1e-6 and val < 1.0 - 1e-6:
                    return False
            elif v.var_type == VariableType.INTEGER:
                if abs(val - round(val)) > 1e-5:
                    return False
        return True

    def _choose_branch_var(self, sol: dict[str, float]) -> tuple[str, float]:
        best_var = ""
        best_frac = 0.0
        for v in self.original.variables:
            if v.var_type in (VariableType.INTEGER, VariableType.BINARY):
                val = sol.get(v.name, 0)
                frac = abs(val - round(val))
                if frac > best_frac + 1e-6:
                    best_frac = frac
                    best_var = v.name
        return best_var, sol[best_var]

    def _is_better(self, z: float) -> bool:
        if self.best_z is None:
            return True
        if self.original.objective_sense == ObjectiveSense.MAX:
            return z > self.best_z + 1e-6
        return z < self.best_z - 1e-6

    def _can_improve(self, z: float) -> bool:
        if self.best_z is None:
            return True
        if self.original.objective_sense == ObjectiveSense.MAX:
            return z > self.best_z + 1e-6
        return z < self.best_z - 1e-6

    def _update_bound(self, z: float) -> None:
        self.upper_bound = z

    def _build_tree(self) -> str:
        if not self.nodes:
            return ""
        lines = []
        children: dict[int | None, list[BBNode]] = {}
        for n in self.nodes:
            children.setdefault(n.parent_id, []).append(n)

        def walk(node: BBNode, prefix: str, is_last: bool):
            connector = "└── " if is_last else "├── "
            status = ""
            if node.prune_reason:
                status = f" [{node.prune_reason}]"
            elif node.status == "integer":
                status = f" [Z={node.z_integer:.4g}]" if node.z_integer else " [inteiro]"
            lines.append(f"{prefix}{connector}Nó {node.id}{status}")
            kids = children.get(node.id, [])
            ext = "    " if is_last else "│   "
            for i, k in enumerate(kids):
                walk(k, prefix + ext, i == len(kids) - 1)

        roots = children.get(None, [])
        for i, r in enumerate(roots):
            walk(r, "Nó 0\n" if r.id == 0 else "", i == len(roots) - 1)
        return "\n".join(lines) if lines else "Nó 0"

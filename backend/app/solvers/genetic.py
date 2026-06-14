from __future__ import annotations

import random
from dataclasses import dataclass, field

from app.models.problem import ObjectiveSense, ProblemModel, VariableType


@dataclass
class GAIndividual:
    chromosome: list[int]
    fitness: float = 0.0
    feasible: bool = True


@dataclass
class GAGeneration:
    generation: int
    population: list[GAIndividual]
    best: GAIndividual
    avg_fitness: float
    operations: list[str] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)


@dataclass
class GeneticResult:
    status: str
    best_solution: dict[str, float]
    best_fitness: float
    best_generation: int
    generations: list[GAGeneration]
    encoding: str
    stop_reason: str


class GeneticSolver:
    def __init__(
        self,
        problem: ProblemModel,
        population_size: int = 10,
        max_generations: int = 20,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.8,
        seed: int = 42,
    ):
        self.problem = problem
        self.pop_size = population_size
        self.max_gen = max_generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        random.seed(seed)
        self.var_names = problem.var_names

    def solve(self) -> GeneticResult:
        generations: list[GAGeneration] = []
        bounds = self._get_bounds()

        pop = []
        for _ in range(self.pop_size):
            chrom = [random.randint(bounds[v][0], bounds[v][1]) for v in self.var_names]
            ind = GAIndividual(chromosome=chrom)
            ind.fitness, ind.feasible = self._evaluate(chrom)
            pop.append(ind)

        gen0_ops = [
            "Codificação: cada cromossomo é um vetor de genes inteiros [x1, x2, ..., xn].",
            f"População inicial: {self.pop_size} indivíduos gerados aleatoriamente.",
        ]
        generations.append(self._record_gen(0, pop, gen0_ops, []))

        best = max(pop, key=lambda x: x.fitness)
        best_generation = 0

        for g in range(1, self.max_gen + 1):
            ops: list[str] = []
            events: list[dict] = []
            new_pop: list[GAIndividual] = [max(pop, key=lambda x: x.fitness)]

            while len(new_pop) < self.pop_size:
                p1 = self._tournament_select(pop)
                p2 = self._tournament_select(pop)
                sel = f"Seleção por torneio: Pai 1 = {p1.chromosome}, Pai 2 = {p2.chromosome}"
                ops.append(sel)
                events.append({
                    "tipo": "selecao",
                    "pai1": p1.chromosome[:],
                    "pai2": p2.chromosome[:],
                    "fitness_pai1": p1.fitness,
                    "fitness_pai2": p2.fitness,
                })

                if random.random() < self.crossover_rate:
                    point = random.randint(1, len(self.var_names) - 1) if len(self.var_names) > 1 else 1
                    c1 = p1.chromosome[:point] + p2.chromosome[point:]
                    c2 = p2.chromosome[:point] + p1.chromosome[point:]
                    cr = f"Cruzamento (ponto {point}): Filho 1 = {c1}, Filho 2 = {c2}"
                    ops.append(cr)
                    events.append({
                        "tipo": "cruzamento",
                        "ponto": point,
                        "pai1": p1.chromosome[:],
                        "pai2": p2.chromosome[:],
                        "filho1": c1[:],
                        "filho2": c2[:],
                    })
                else:
                    c1, c2 = p1.chromosome[:], p2.chromosome[:]
                    events.append({"tipo": "sem_cruzamento", "descricao": "Pais copiados sem crossover"})

                for chrom in [c1, c2]:
                    mutated = chrom[:]
                    for i in range(len(mutated)):
                        if random.random() < self.mutation_rate:
                            lo, hi = bounds[self.var_names[i]]
                            old = mutated[i]
                            mutated[i] = random.randint(lo, hi)
                            mut = f"Mutação: gene {i} ({self.var_names[i]}): {old} → {mutated[i]}"
                            ops.append(mut)
                            events.append({
                                "tipo": "mutacao",
                                "indice": i,
                                "variavel": self.var_names[i],
                                "antes": old,
                                "depois": mutated[i],
                            })
                    ind = GAIndividual(chromosome=mutated)
                    ind.fitness, ind.feasible = self._evaluate(mutated)
                    new_pop.append(ind)

            pop = new_pop[: self.pop_size]
            gen_best = max(pop, key=lambda x: x.fitness)
            generations.append(self._record_gen(g, pop, ops, events))

            if gen_best.fitness > best.fitness + 1e-6:
                best = gen_best
                best_generation = g

        stop = (
            f"{self.max_gen} gerações evolutivas (+ população inicial), "
            f"população {self.pop_size}, mutação {self.mutation_rate}, cruzamento {self.crossover_rate}"
        )

        solution = {
            self.var_names[i]: float(best.chromosome[i]) for i in range(len(self.var_names))
        }

        return GeneticResult(
            status="completed",
            best_solution=solution,
            best_fitness=best.fitness,
            best_generation=best_generation,
            generations=generations,
            encoding="Vetor inteiro [x1, x2, ..., xn] — cada gene é o valor de uma variável.",
            stop_reason=stop,
        )

    def _get_bounds(self) -> dict[str, tuple[int, int]]:
        bounds: dict[str, tuple[int, int]] = {}
        for v in self.problem.variables:
            if v.var_type == VariableType.BINARY:
                bounds[v.name] = (0, 1)
            else:
                hi = int(v.upper_bound) if v.upper_bound else 10
                bounds[v.name] = (max(0, int(v.lower_bound)), max(hi, 5))
        return bounds

    def _evaluate(self, chrom: list[int]) -> tuple[float, bool]:
        sol = {self.var_names[i]: chrom[i] for i in range(len(self.var_names))}
        penalty = 0.0
        feasible = True

        for cst in self.problem.constraints:
            lhs = sum(cst.coefficients.get(v, 0) * sol.get(v, 0) for v in self.var_names)
            if cst.sense == "<=" and lhs > cst.rhs + 1e-6:
                penalty += 1000 * (lhs - cst.rhs)
                feasible = False
            elif cst.sense == ">=" and lhs < cst.rhs - 1e-6:
                penalty += 1000 * (cst.rhs - lhs)
                feasible = False

        z = sum(self.problem.objective.get(v, 0) * sol.get(v, 0) for v in self.var_names)
        if self.problem.objective_sense == ObjectiveSense.MAX:
            fitness = z - penalty
        else:
            fitness = -z - penalty
        return fitness, feasible

    def _tournament_select(self, pop: list[GAIndividual], k: int = 3) -> GAIndividual:
        candidates = random.sample(pop, min(k, len(pop)))
        return max(candidates, key=lambda x: x.fitness)

    def _record_gen(
        self,
        gen: int,
        pop: list[GAIndividual],
        ops: list[str],
        events: list[dict],
    ) -> GAGeneration:
        best = max(pop, key=lambda x: x.fitness)
        avg = sum(p.fitness for p in pop) / len(pop)
        return GAGeneration(
            generation=gen,
            population=pop[:],
            best=best,
            avg_fitness=avg,
            operations=ops,
            events=events,
        )

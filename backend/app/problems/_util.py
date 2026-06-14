from __future__ import annotations

from app.models.problem import (
    Constraint,
    ObjectiveSense,
    ProblemModel,
    Variable,
    VariableType,
)


def make_model(
    sense: ObjectiveSense,
    objective: dict[str, float],
    constraints: list[Constraint],
    variables: list[Variable],
    description: str,
) -> ProblemModel:
    return ProblemModel(
        objective_sense=sense,
        objective=objective,
        constraints=constraints,
        variables=variables,
        description=description,
    )


def bin_vars(names: list[str]) -> list[Variable]:
    return [Variable(n, VariableType.BINARY) for n in names]


def int_vars(names: list[str]) -> list[Variable]:
    return [Variable(n, VariableType.INTEGER) for n in names]


def cont_vars(names: list[str]) -> list[Variable]:
    return [Variable(n, VariableType.CONTINUOUS) for n in names]

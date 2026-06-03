from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Literal


class ObjectiveSense(str, Enum):
    MAX = "max"
    MIN = "min"


class VariableType(str, Enum):
    CONTINUOUS = "continuous"
    INTEGER = "integer"
    BINARY = "binary"


@dataclass
class Variable:
    name: str
    var_type: VariableType = VariableType.CONTINUOUS
    lower_bound: float = 0.0
    upper_bound: float | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "var_type": self.var_type.value,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
        }


@dataclass
class Constraint:
    coefficients: dict[str, float]
    sense: Literal["<=", ">=", "="]
    rhs: float
    name: str | None = None

    def to_dict(self) -> dict:
        return {
            "coefficients": self.coefficients,
            "sense": self.sense,
            "rhs": self.rhs,
            "name": self.name,
        }


@dataclass
class ProblemModel:
    objective_sense: ObjectiveSense
    objective: dict[str, float]
    constraints: list[Constraint]
    variables: list[Variable]
    description: str | None = None

    @property
    def var_names(self) -> list[str]:
        return [v.name for v in self.variables]

    @property
    def n_vars(self) -> int:
        return len(self.variables)

    @property
    def n_constraints(self) -> int:
        return len(self.constraints)

    def has_integer_vars(self) -> bool:
        return any(v.var_type != VariableType.CONTINUOUS for v in self.variables)

    def has_binary_vars(self) -> bool:
        return any(v.var_type == VariableType.BINARY for v in self.variables)

    def problem_category(self) -> str:
        types = {v.var_type for v in self.variables}
        if types == {VariableType.CONTINUOUS}:
            return "PL"
        if types <= {VariableType.BINARY, VariableType.CONTINUOUS} and VariableType.BINARY in types:
            if all(v.var_type == VariableType.BINARY for v in self.variables):
                return "PLIB"
            return "PLIM"
        if VariableType.INTEGER in types or VariableType.BINARY in types:
            return "PLI"
        return "PL"

    def to_dict(self) -> dict:
        return {
            "objective_sense": self.objective_sense.value,
            "objective": self.objective,
            "constraints": [c.to_dict() for c in self.constraints],
            "variables": [v.to_dict() for v in self.variables],
            "description": self.description,
        }

    def model_copy(self, deep: bool = False) -> ProblemModel:
        import copy

        if deep:
            return copy.deepcopy(self)
        return copy.copy(self)

    def model_dump(self) -> dict:
        return self.to_dict()

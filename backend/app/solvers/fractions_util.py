from __future__ import annotations

from fractions import Fraction

import numpy as np

MAX_DENOMINATOR = 10_000


def to_fraction(x: float) -> Fraction:
    if abs(x) < 1e-12:
        return Fraction(0)
    return Fraction(x).limit_denominator(MAX_DENOMINATOR)


def frac_str(x: float) -> str:
    f = to_fraction(x)
    if f.denominator == 1:
        return str(f.numerator)
    return f"{f.numerator}/{f.denominator}"


def frac_div_str(numerator: float, denominator: float) -> str:
    if abs(denominator) < 1e-12:
        return "—"
    return frac_str(numerator / denominator)


def matrix_to_frac_str(matrix: np.ndarray) -> list[list[str]]:
    return [[frac_str(float(v)) for v in row] for row in matrix]

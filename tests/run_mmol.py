#!/usr/bin/env python3
"""Testa as 10 instâncias padrão da Lista MMOL."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestrator import solve_mmol  # noqa: E402
from app.problems.registry import MMOL_PROBLEMS  # noqa: E402


def main() -> int:
    falhas = 0
    for key in MMOL_PROBLEMS:
        t0 = time.perf_counter()
        try:
            r = solve_mmol(key)
            z = r["6_interpretacao"]["solucao"].get("valor_objetivo")
            dt = time.perf_counter() - t0
            des = r["4_resolucao"].get("branch_and_bound", {}).get("desempenho", {})
            nos = des.get("nos_explorados", "?")
            status = "OK" if z is not None else "SEM_SOL"
            if z is None:
                falhas += 1
            print(f"[{status}] {key}: Z={z}, {dt:.1f}s, nos={nos}")
        except Exception as e:
            falhas += 1
            print(f"[ERR] {key}: {e}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())

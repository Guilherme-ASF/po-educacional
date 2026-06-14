#!/usr/bin/env python3
"""Executa os casos de teste documentados e imprime resultados para o relatório."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.orchestrator import solve_educational  # noqa: E402

CASOS = [
    {
        "id": "caso1",
        "arquivo": "caso1_plip_enunciado.txt",
        "metodo": "Branch and Bound",
        "esperado_z": 40.0,
        "esperado": {"x1": 5.0, "x2": 0.0},
    },
    {
        "id": "caso2",
        "arquivo": "caso2_pl_continuo.txt",
        "metodo": "Método Gráfico",
        "esperado_z": 9.0,
        "esperado": {"x1": 1.0, "x2": 3.0},
    },
    {
        "id": "caso3",
        "arquivo": "caso3_plip_maior.txt",
        "metodo": "Branch and Bound",
        "esperado_z": 42.0,
        "esperado": {"x1": 1.0, "x2": 4.0, "x3": 0.0},
    },
]


def main() -> int:
    casos_dir = Path(__file__).parent / "casos"
    resultados = []
    falhas = 0

    for caso in CASOS:
        texto = (casos_dir / caso["arquivo"]).read_text(encoding="utf-8")
        r = solve_educational(texto, caso["metodo"])
        sol = r["6_interpretacao"]["solucao"]
        z = sol.get("valor_objetivo")
        vars_ = sol.get("variaveis", {})
        bb = r["4_resolucao"].get("branch_and_bound", {})
        desemp = bb.get("desempenho", {})

        ok_z = z is not None and abs(z - caso["esperado_z"]) < 1e-3
        ok_vars = all(
            abs(vars_.get(k, 0) - v) < 1e-3 for k, v in caso["esperado"].items()
        )
        ok = ok_z and ok_vars
        if not ok:
            falhas += 1

        resultados.append(
            {
                "id": caso["id"],
                "metodo": caso["metodo"],
                "ok": ok,
                "z_obtido": z,
                "z_esperado": caso["esperado_z"],
                "variaveis": vars_,
                "desempenho": desemp,
            }
        )
        status = "OK" if ok else "FALHA"
        print(f"[{status}] {caso['id']}: Z={z}, vars={vars_}, desempenho={desemp}")

    out = Path(__file__).parent / "resultados_casos.json"
    out.write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResultados salvos em {out}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())

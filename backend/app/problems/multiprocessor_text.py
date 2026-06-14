from __future__ import annotations

import re
from typing import Any


def task_label(i: int) -> str:
    return f"t{i + 1}"


def server_label(j: int) -> str:
    return f"s{j + 1}"


def var_name(task: str, server: str) -> str:
    return f"x_{task}_{server}"


def multiprocessor_to_text(data: dict[str, Any]) -> str:
    """Modelagem em DSL simplificada (@dados + modelo compacto)."""
    tempos: list[list[float]] = data["tempos"]
    cap = float(data["capacidade"])
    n_srv = len(tempos)
    n_task = len(tempos[0])
    tasks = [task_label(i) for i in range(n_task)]
    servers = [server_label(j) for j in range(n_srv)]

    lines = [
        "# ══════════════════════════════════════════════════════════",
        "# GUIA RÁPIDO",
        "#   p(t,s)  → tempo da tarefa t no servidor s (dado fixo)",
        "#   x[t,s]  → 1 se tarefa t alocada ao servidor s",
        "#   M       → makespan (tempo máximo entre servidores)",
        "#   ∀  Σ    → quantificador / somatório",
        "# Edite @dados para mudar tempos e capacidade.",
        "# ══════════════════════════════════════════════════════════",
        "",
        "# Problema 1 — Alocação em sistema multiprocessador",
        "# Minimizar M sujeito a cada tarefa em um servidor e capacidade C.",
        "",
        "@dados",
        f"tarefas = {', '.join(tasks)}",
        f"servidores = {', '.join(servers)}",
        f"C = {int(cap) if cap == int(cap) else cap}",
        "p:",
    ]
    for i, t in enumerate(tasks):
        parts = [
            f"{s}={int(tempos[j][i]) if tempos[j][i] == int(tempos[j][i]) else tempos[j][i]}"
            for j, s in enumerate(servers)
        ]
        lines.append(f"  {t}: {', '.join(parts)}")

    lines.extend(
        [
            "",
            "@modelo",
            "min M",
            "",
            "# cada tarefa em exatamente um servidor",
            "∀ t: Σ_s x[t,s] = 1",
            "",
            "# capacidade de cada servidor",
            "∀ s: Σ_t p(t,s)·x[t,s] ≤ C",
            "",
            "# makespan: M = max_s Σ_t p(t,s)·x[t,s]",
            "∀ s: Σ_t p(t,s)·x[t,s] ≤ M",
            "",
            "@dominio",
            "M ≥ 0",
            "x[t,s] ∈ {0,1}",
        ]
    )
    return "\n".join(lines)


def extract_instance_from_text(text: str) -> dict[str, Any] | None:
    """Extrai tempos e capacidade de @dados ou comentários p[t,s]."""
    from app.parsers.model_dsl import _parse_dados_block

    dados = _parse_dados_block(text)
    if dados:
        tasks = dados["tarefas"]
        servers = dados["servidores"]
        tempos = [
            [dados["p"].get((t, s), 0.0) for t in tasks]
            for s in servers
        ]
        return {"tempos": tempos, "capacidade": dados["capacidade"]}

    p_coefs: dict[tuple[str, str], float] = {}
    cap: float | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        for m in re.finditer(
            r"p\s*\[\s*([^,\]]+)\s*,\s*([^\]]+)\s*\]\s*=\s*(\d+(?:\.\d+)?)",
            stripped,
            re.I,
        ):
            t, s, v = m.group(1).strip(), m.group(2).strip(), float(m.group(3))
            p_coefs[(t, s)] = v
        cap_m = re.search(
            r"(?:capacidade|cap)\s*[=:c]\s*(\d+(?:\.\d+)?)",
            stripped,
            re.I,
        )
        if cap_m:
            cap = float(cap_m.group(1))

    if not p_coefs or cap is None:
        return None

    tasks = sorted({t for t, _ in p_coefs}, key=_label_key)
    servers = sorted({s for _, s in p_coefs}, key=_label_key)
    tempos = [[p_coefs.get((t, s), 0.0) for t in tasks] for s in servers]
    return {"tempos": tempos, "capacidade": cap}


def _label_key(label: str) -> tuple[str, int]:
    m = re.match(r"([a-zA-Z]+)(\d+)", label)
    if m:
        return (m.group(1).lower(), int(m.group(2)))
    return (label.lower(), 0)

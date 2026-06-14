from __future__ import annotations

import re


def expand_model_dsl(text: str) -> str:
    """Converte blocos @dados / @modelo / @dominio em modelagem expandida."""
    if "@dados" not in text.lower() and "@modelo" not in text.lower():
        return text

    dados = _parse_dados_block(text)
    if not dados:
        return text

    tasks = dados["tarefas"]
    servers = dados["servidores"]
    cap = dados["capacidade"]
    p_coefs = dados["p"]
    task_list = ", ".join(tasks)
    server_list = ", ".join(servers)

    lines = [
        "# ── Legenda ──",
        "# p(t,s) = DADO: tempo da tarefa t no servidor s (edite em @dados)",
        "# x[t,s] = VARIÁVEL binária: 1 se a tarefa t for alocada ao servidor s",
        "# M      = VARIÁVEL contínua: makespan (maior carga entre servidores)",
        "",
        "Min Z = M",
        "",
        "S.A.",
        "",
        f"# Tarefas: {task_list} | Servidores: {server_list} | Capacidade C = {cap}",
        "",
        "# Cada tarefa em exatamente um servidor",
        f"∀t ∈ {{{task_list}}}: Σ_s x_{{t,s}} = 1",
        "",
        "# Capacidade de cada servidor",
        f"∀s ∈ {{{server_list}}}: Σ_t p[t,s]·x_{{t,s}} ≤ {cap}",
        "",
        "# Makespan: M = max_s Σ_t p[t,s]·x_{t,s}",
        f"∀s ∈ {{{server_list}}}: Σ_t p[t,s]·x_{{t,s}} ≤ M",
        "",
        "# Tempos p[t,s] (gerados a partir de @dados)",
    ]
    for t in tasks:
        parts = [
            f"p[{t},{s}]={_fmt(p_coefs.get((t, s), 0))}"
            for s in servers
        ]
        lines.append("#   " + "  ".join(parts))

    lines.extend(["", "M >= 0", f"x_{{t,s}} binário ∀ t ∈ {{{task_list}}}, s ∈ {{{server_list}}}"])
    return "\n".join(lines)


def _parse_dados_block(text: str) -> dict | None:
    m = re.search(r"@dados\s*(.*?)(?=@modelo|@dominio|\Z)", text, re.I | re.S)
    if not m:
        return None

    block = m.group(1)
    tasks: list[str] = []
    servers: list[str] = []
    cap: float | None = None
    p_coefs: dict[tuple[str, str], float] = {}

    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        tm = re.match(r"tarefas?\s*=\s*(.+)", line, re.I)
        if tm:
            tasks = _split_list(tm.group(1))
            continue

        sm = re.match(r"servidores?\s*=\s*(.+)", line, re.I)
        if sm:
            servers = _split_list(sm.group(1))
            continue

        cm = re.match(r"(?:C|capacidade)\s*=\s*(\d+(?:\.\d+)?)", line, re.I)
        if not cm:
            cm = re.match(r"capacidade\s+c\s*=\s*(\d+(?:\.\d+)?)", line, re.I)
        if cm:
            cap = float(cm.group(1))
            continue

        row = re.match(r"([a-z]\d+)\s*:\s*(.+)", line, re.I)
        if row:
            t = row.group(1)
            tasks.append(t)
            for pm in re.finditer(r"([a-z]\d+)\s*=\s*(\d+(?:\.\d+)?)", row.group(2), re.I):
                s, v = pm.group(1), float(pm.group(2))
                servers.append(s)
                p_coefs[(t, s)] = v
            continue

        for pm in re.finditer(
            r"p\s*[\[(]\s*([^,\])]+)\s*,\s*([^\])]+)\s*[\])]\s*=\s*(\d+(?:\.\d+)?)",
            line,
            re.I,
        ):
            t, s, v = pm.group(1).strip(), pm.group(2).strip(), float(pm.group(3))
            tasks.append(t)
            servers.append(s)
            p_coefs[(t, s)] = v

    tasks = _unique_sorted(tasks)
    servers = _unique_sorted(servers)
    if not tasks or not servers or not p_coefs or cap is None:
        return None
    return {"tarefas": tasks, "servidores": servers, "capacidade": cap, "p": p_coefs}


def _split_list(s: str) -> list[str]:
    return [x.strip() for x in re.split(r",\s*", s.strip()) if x.strip()]


def _unique_sorted(labels: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for lb in labels:
        seen[lb] = None
    return sorted(seen.keys(), key=_label_key)


def _label_key(label: str) -> tuple[str, int]:
    m = re.match(r"([a-zA-Z]+)(\d+)", label)
    if m:
        return (m.group(1).lower(), int(m.group(2)))
    return (label.lower(), 0)


def _fmt(v: float) -> str:
    return str(int(v)) if v == int(v) else str(v)

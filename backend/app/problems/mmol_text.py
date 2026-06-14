from __future__ import annotations

from typing import Any, Callable

from app.problems.multiprocessor_text import multiprocessor_to_text

_HEADER = (
    "# ══════════════════════════════════════════════════════════\n"
    "# GUIA RÁPIDO\n"
    "#   p(·), c[i], d[t], l[t]  → parâmetros fixos da instância\n"
    "#   x[·], y[j], z[p], q[i]  → variáveis de decisão\n"
    "#   M                         → makespan / Big-M (quando usado)\n"
    "#   ∀  Σ  ∈                   → quantificador, somatório, pertence a\n"
    "# Edite @dados para mudar a instância; @modelo é a formulação.\n"
    "# ══════════════════════════════════════════════════════════"
)


def mmol_to_text(chave: str, data: dict[str, Any]) -> str:
    fn = _TEXT_BUILDERS.get(chave)
    if fn is None:
        raise ValueError(f"Sem modelagem compacta para: {chave}")
    return fn(data)


def project_selection_to_text(data: dict[str, Any]) -> str:
    custos = [int(c) for c in data["custos"]]
    impactos = [int(v) for v in data["impactos"]]
    budget = int(data["orcamento"])
    projs = [f"P{i + 1}" for i in range(len(custos))]

    return "\n".join(
        [
            _HEADER,
            "",
            "# Problema 2 — Seleção de projetos (PIB / knapsack 0-1)",
            "# x[i]=1 se o projeto i é aprovado; maximizar impacto total no orçamento.",
            "",
            "@dados",
            f"projetos = {', '.join(projs)}",
            "custo c[i]: " + ", ".join(f"{projs[i]}={custos[i]}" for i in range(len(projs))),
            "impacto v[i]: " + ", ".join(f"{projs[i]}={impactos[i]}" for i in range(len(projs))),
            f"orcamento B = {budget}",
            "",
            "@modelo",
            "max Σ_i v[i]·x[i]",
            "",
            f"# orçamento total não pode exceder B={budget}",
            "Σ_i c[i]·x[i] ≤ B",
            "",
            "# ── Regras lógicas desta instância ──",
            "x[P3] ≤ x[P1]              # P3 só se P1 aprovado",
            "x[P4] + x[P5] ≤ 1          # P4 e P5 são mutuamente excludentes",
            "x[P1] + x[P2] + x[P4] ≥ 2  # ao menos 2 entre {P1,P2,P4}",
            "",
            "@dominio",
            "x[i] ∈ {0,1}",
        ]
    )


def knapsack_md_to_text(data: dict[str, Any]) -> str:
    banda = [int(b) for b in data["banda"]]
    buffer = [int(b) for b in data["buffer"]]
    prio = [int(p) for p in data["prioridade"]]
    cap_b = int(data["cap_banda"])
    cap_u = int(data["cap_buffer"])
    fluxos = [f"F{i + 1}" for i in range(len(prio))]

    return "\n".join(
        [
            _HEADER,
            "",
            "# Problema 3 — Knapsack multidimensional (seleção de fluxos)",
            "# x[j]=1 ativa o fluxo j; dois recursos limitados: banda e buffer.",
            "",
            "@dados",
            f"fluxos = {', '.join(fluxos)}",
            "banda b[j]: " + ", ".join(f"{fluxos[j]}={banda[j]}" for j in range(len(fluxos))),
            "buffer u[j]: " + ", ".join(f"{fluxos[j]}={buffer[j]}" for j in range(len(fluxos))),
            "prioridade w[j]: " + ", ".join(f"{fluxos[j]}={prio[j]}" for j in range(len(fluxos))),
            f"cap_banda = {cap_b}",
            f"cap_buffer = {cap_u}",
            "",
            "@modelo",
            "max Σ_j w[j]·x[j]          # maximizar prioridade total",
            "",
            f"Σ_j b[j]·x[j] ≤ {cap_b}    # limite de banda (Mbps)",
            f"Σ_j u[j]·x[j] ≤ {cap_u}    # limite de buffer (GB)",
            "",
            "@dominio",
            "x[j] ∈ {0,1}",
        ]
    )


def production_setup_to_text(data: dict[str, Any]) -> str:
    setup = [int(s) for s in data["setup"]]
    vc = [int(v) for v in data["var_cost"]]
    rev = [int(r) for r in data["receita"]]
    dem = [int(d) for d in data["demanda_min"]]
    cap_u = int(data["cap_unidades"])
    cap_h = int(data["cap_horas"])
    horas = data["horas"]
    prods = [f"Prod{i + 1}" for i in range(len(setup))]

    lines = [
        _HEADER,
        "",
        "# Problema 5 — Produção com custo fixo de setup (PLIM)",
        "# q[i] = quantidade do produto i; y[i]=1 se a linha i é ativada (paga setup).",
        "",
        "@dados",
        f"produtos = {', '.join(prods)}",
        "setup s[i]: " + ", ".join(f"{prods[i]}={setup[i]}" for i in range(len(prods))),
        "custo var. cv[i]: " + ", ".join(f"{prods[i]}={vc[i]}" for i in range(len(prods))),
        "receita r[i]: " + ", ".join(f"{prods[i]}={rev[i]}" for i in range(len(prods))),
        "demanda min d[i]: " + ", ".join(f"{prods[i]}={dem[i]}" for i in range(len(prods))),
        "horas h[i]: " + ", ".join(
            f"{prods[i]}={int(horas[i]) if horas[i] == int(horas[i]) else horas[i]}"
            for i in range(len(prods))
        ),
        f"cap_unidades = {cap_u}",
        f"cap_horas = {cap_h}",
        f"M = {cap_u}   # Big-M (capacidade usada na ligação q[i] ≤ M·y[i])",
        "",
        "@modelo",
        "max Σ_i (r[i] - cv[i])·q[i] - Σ_i s[i]·y[i]   # lucro = margem - setup",
        "",
        f"Σ_i q[i] ≤ {cap_u}                 # capacidade total de unidades",
        f"Σ_i h[i]·q[i] ≤ {cap_h}            # capacidade total de horas",
        "∀ i: q[i] ≥ d[i]                   # demanda mínima",
        "∀ i: q[i] ≤ M·y[i]                 # só produz se linha i ativa",
        "",
        "@dominio",
        "q[i] ≥ 0     (contínua)",
        "y[i] ∈ {0,1}",
    ]
    return "\n".join(lines)


def set_covering_to_text(data: dict[str, Any]) -> str:
    custos = [int(c) for c in data["custos"]]
    cobertura: list[list[int]] = data["cobertura"]
    n_zonas = int(data["n_zonas"])
    locais = [f"L{j + 1}" for j in range(len(custos))]
    zonas = [f"Z{z}" for z in range(1, n_zonas + 1)]

    lines = [
        _HEADER,
        "",
        "# Problema 6 — Set covering (cobertura de zonas)",
        "# x[j]=1 instala antena/local j; cada zona deve ser coberta por ≥1 local.",
        "",
        "@dados",
        f"locais = {', '.join(locais)}",
        f"zonas = {', '.join(zonas)}",
        "custo c[j]: " + ", ".join(f"{locais[j]}={custos[j]}" for j in range(len(locais))),
        "# cobertura S[j] ⊆ zonas atendidas pelo local j:",
    ]
    for j, loc in enumerate(locais):
        zs = ", ".join(f"Z{z}" for z in cobertura[j])
        lines.append(f"#   S[{loc}] = {{{zs}}}")

    lines.extend(
        [
            "",
            "@modelo",
            "min Σ_j c[j]·x[j]          # minimizar custo de instalação",
            "",
            "# cada zona z coberta por ao menos um local que a alcance",
            "∀ z: Σ_{j: z∈S[j]} x[j] ≥ 1",
            "",
            "@dominio",
            "x[j] ∈ {0,1}",
        ]
    )
    return "\n".join(lines)


def bin_packing_to_text(data: dict[str, Any]) -> str:
    demandas: list[float] = data["demandas"]
    cap = float(data["capacidade"])
    vms = [f"v{i + 1}" for i in range(len(demandas))]
    bins = [f"b{j + 1}" for j in range(len(demandas))]
    vm_list = ", ".join(vms)
    bin_list = ", ".join(bins)
    dem_lines = ", ".join(
        f"{v}={int(d) if d == int(d) else d}" for v, d in zip(vms, demandas)
    )
    cap_s = int(cap) if cap == int(cap) else cap

    return "\n".join(
        [
            _HEADER,
            "",
            "# Problema 4 — Bin packing (escalonamento de VMs em servidores)",
            "# x[i,j]=1: VM i no servidor j; y[j]=1: servidor j é usado.",
            "# Objetivo: minimizar Σ y[j] (número de servidores).",
            "",
            "@dados",
            f"vms = {vm_list}",
            f"bins = {bin_list}",
            f"demandas: {dem_lines}",
            f"capacidade = {cap_s}",
            "",
            "@modelo",
            "min Σ_j y[j]",
            "",
            "# cada VM em exatamente um bin",
            "∀ i: Σ_j x[i,j] = 1",
            "",
            "# capacidade: só aloca em bin j se y[j]=1",
            f"∀ j: Σ_i d[i]·x[i,j] ≤ {cap_s}·y[j]",
            "",
            "# ligação x[i,j] ≤ y[j]  (implícita na restrição acima)",
            "# simetria: evita permutar bins vazios",
            "∀ j>1: y[j] ≤ y[j-1]",
            "",
            "@dominio",
            "x[i,j] ∈ {0,1}",
            "y[j] ∈ {0,1}",
        ]
    )


def tsp_to_text(data: dict[str, Any]) -> str:
    dist: list[list[float]] = data["distancias"]
    n = len(dist)
    cities = [f"c{i}" for i in range(n)]
    city_list = ", ".join(cities)

    lines = [
        _HEADER,
        "",
        "# Problema 7 — TSP com eliminação de subtours (Miller-Tucker-Zemlin)",
        "# x[i,j]=1 se o arco i→j está no tour; c0 = depósito (início e fim).",
        "# u[i] contínuas auxiliares eliminam subtours (formulção MTZ).",
        "",
        "@dados",
        f"cidades = {city_list}",
        f"n = {n}",
        "# custo c[i,j] — matriz (0 na diagonal):",
    ]
    for i, row in enumerate(dist):
        vals = "  ".join(
            f"c[{cities[i]},{cities[j]}]={int(v) if v == int(v) else v}"
            for j, v in enumerate(row)
            if i != j
        )
        if vals:
            lines.append(f"#   {vals}")

    others = ", ".join(cities[1:])
    lines.extend(
        [
            "",
            "@modelo",
            "min Σ_{i≠j} c[i,j]·x[i,j]",
            "",
            "# fluxo: cada cidade (exceto depósito) tem 1 entrada e 1 saída",
            f"∀ j ∈ {{{others}}}: Σ_i x[i,j] = 1",
            f"∀ i ∈ {{{others}}}: Σ_j x[i,j] = 1",
            "",
            "# tour parte e retorna ao depósito c0",
            f"Σ_{{j≠c0}} x[c0,j] = 1",
            f"Σ_{{i≠c0}} x[i,c0] = 1",
            "",
            "# MTZ: u[i] - u[j] + n·x[i,j] ≤ n-1  (elimina subtours)",
            f"∀ i,j ∈ {{{others}}}, i≠j:",
            f"  u[i] - u[j] + {n}·x[i,j] ≤ {n - 1}",
            "",
            "@dominio",
            "x[i,j] ∈ {0,1}",
            "u[i] ≥ 0  (contínuas)",
        ]
    )
    return "\n".join(lines)


def facility_location_to_text(data: dict[str, Any]) -> str:
    hij = data["custos_atend"]
    fj = data["instalacao"]
    max_c = int(data["max_cidades"])
    budget = float(data["orcamento"])
    n_reg = len(hij)
    n_cid = len(fj)
    regs = [f"r{i + 1}" for i in range(n_reg)]
    cids = [f"c{j + 1}" for j in range(n_cid)]
    reg_list = ", ".join(regs)
    cid_list = ", ".join(cids)

    lines = [
        _HEADER,
        "",
        "# Problema 8 — Localização de instalações (facility location)",
        "# y[j]=1 abre cidade j (custo fixo f[j]); x[i,j]=1 atende região i por j.",
        "",
        "@dados",
        f"regioes = {reg_list}",
        f"cidades = {cid_list}",
        f"max_cidades = {max_c}",
        f"orcamento = {int(budget) if budget == int(budget) else budget}",
        "# custo fixo f[j] de abrir cidade j:",
        "f: " + ", ".join(f"{cids[j]}={int(fj[j]) if fj[j]==int(fj[j]) else fj[j]}" for j in range(n_cid)),
        "# custo h[i,j] de atender região i por cidade j:",
    ]
    for i, reg in enumerate(regs):
        parts = "  ".join(
            f"h[{reg},{cids[j]}]={int(hij[i][j]) if hij[i][j]==int(hij[i][j]) else hij[i][j]}"
            for j in range(n_cid)
        )
        lines.append(f"#   {parts}")

    lines.extend(
        [
            "",
            "@modelo",
            "min Σ_j f[j]·y[j] + Σ_{i,j} h[i,j]·x[i,j]",
            "",
            "# cada região atendida por exatamente uma cidade",
            "∀ i: Σ_j x[i,j] = 1",
            "",
            "# só atende se a cidade estiver aberta",
            "∀ i,j: x[i,j] ≤ y[j]",
            "",
            f"# no máximo {max_c} cidades abertas",
            f"Σ_j y[j] ≤ {max_c}",
            "",
            f"# orçamento total de instalação",
            f"Σ_j f[j]·y[j] ≤ {int(budget) if budget == int(budget) else budget}",
            "",
            "@dominio",
            "x[i,j] ∈ {0,1}",
            "y[j] ∈ {0,1}",
        ]
    )
    return "\n".join(lines)


def timetabling_to_text(data: dict[str, Any]) -> str:
    salas = data["salas"]
    horarios = data["horarios"]
    disciplinas = data["disciplinas"]
    pts: dict[tuple[str, str, str], int] = {
        tuple(k): v for k, v in data["pontuacoes"].items()
    }

    lines = [
        _HEADER,
        "",
        "# Problema 10 — Grade de horários (timetabling)",
        "# x[d,s,h]=1 aloca disciplina d na sala s no horário h.",
        "# Só existem variáveis para combinações (d,s,h) com pontuação > 0.",
        "",
        "@dados",
        f"salas = {', '.join(salas)}",
        f"horarios = {', '.join(horarios)}",
        f"disciplinas = {', '.join(disciplinas)}",
        "# pontuação p[d,s,h] (omitida se não houver aula possível):",
    ]
    for d in disciplinas:
        for s in salas:
            for h in horarios:
                if (d, s, h) in pts:
                    lines.append(f"#   p[{d},{s},{h}] = {pts[(d, s, h)]}")

    lines.extend(
        [
            "",
            "@modelo",
            "max Σ_{d,s,h} p[d,s,h]·x[d,s,h]",
            "",
            "# cada disciplina em exatamente um (sala, horário)",
            "∀ d: Σ_{s,h} x[d,s,h] = 1",
            "",
            "# no máximo uma disciplina por slot (sala, horário)",
            "∀ s,h: Σ_d x[d,s,h] ≤ 1",
            "",
            "# ── Regras pedagógicas desta instância ──",
            "∀ s: x[D1,s,H4] = 0                    # D1 não no H4",
            "∀ s≠S3, ∀ h: x[D3,s,h] = 0             # D3 só na S3",
            "∀ h: x[D4,S3,h] = 0                    # D4 só em S1 ou S2",
            "∀ s, ∀ h∈{H1,H2}: x[D4,s,h] = 0        # D4 só em H3 ou H4",
            "∀ h: Σ_s x[D1,s,h] + Σ_s x[D3,s,h] ≤ 1 # D1 e D3 em horários distintos",
            "Σ_{s,h} idx(h)·x[D2,s,h] ≤ Σ_{s,h} idx(h)·x[D4,s,h]  # D2 antes de D4",
            "",
            "@dominio",
            "x[d,s,h] ∈ {0,1}  (apenas onde p[d,s,h] existe)",
        ]
    )
    return "\n".join(lines)


def _fmt_pattern_line(
    p_idx: int,
    pat: list[int],
    types: list[str],
    comp: list[int],
    bloco: int,
) -> str:
    parts = [f"{pat[r]}×{types[r]}" for r in range(len(pat)) if pat[r] > 0]
    uso = sum(pat[r] * comp[r] for r in range(len(pat)))
    sobra = bloco - uso
    body = " + ".join(parts) if parts else "(vazio)"
    return f"#   p{p_idx}: {body}  (usa {uso}, sobra {sobra})"


def cutting_stock_to_text(data: dict[str, Any]) -> str:
    from app.problems.cutting_stock import _gerar_padroes

    comp = [int(c) for c in data["comprimentos"]]
    dem = [int(d) for d in data["demandas"]]
    bloco = int(data["bloco"])
    types = [f"T{i + 1}" for i in range(len(comp))]
    type_list = ", ".join(types)
    padroes = _gerar_padroes(comp, bloco)
    n_pat = len(padroes)
    p_list = ", ".join(f"p{i + 1}" for i in range(n_pat))

    lines = [
        _HEADER,
        "",
        "# Problema 9 — Cutting stock (corte de bobinas / rolos)",
        "# z[p] = quantos blocos de comprimento L são cortados com o padrão p.",
        "# Cada padrão p indica quantas peças a[t,p] de cada tipo cabem num bloco.",
        "",
        "@dados",
        f"tipos = {type_list}",
        "l[t]: " + ", ".join(f"{types[i]}={comp[i]}" for i in range(len(comp))),
        "d[t]: " + ", ".join(f"{types[i]}={dem[i]}" for i in range(len(comp))),
        f"L = {bloco}   # comprimento de cada bloco (rolo)",
        f"P = {{{p_list}}}   # {n_pat} padrões de corte factíveis",
        "# a[t,p] — peças do tipo t no padrão p (só combinações com soma ≤ L):",
    ]
    for i, pat in enumerate(padroes):
        lines.append(_fmt_pattern_line(i + 1, pat, types, comp, bloco))

    dem_rhs = ", ".join(f"{dem[i]}" for i in range(len(dem)))
    lines.extend(
        [
            "",
            "@modelo",
            "min Σ_{p∈P} z[p]          # minimizar número de blocos usados",
            "",
            "# atender demanda de cada tipo de peça",
            f"∀ t: Σ_{{p∈P}} a[t,p]·z[p] ≥ d[t]    # d = ({dem_rhs})",
            "",
            "@dominio",
            "z[p] ∈ {0,1,2,...}   (inteiro não negativo)",
            "",
            "# Nota: a formulação expandida usa z1..z"
            + str(n_pat)
            + " e uma restrição ≥ por tipo.",
        ]
    )
    return "\n".join(lines)


_TEXT_BUILDERS: dict[str, Callable[[dict[str, Any]], str]] = {
    "1_multiprocessador": multiprocessor_to_text,
    "2_selecao_projetos": project_selection_to_text,
    "3_knapsack_multidimensional": knapsack_md_to_text,
    "4_bin_packing": bin_packing_to_text,
    "5_setup_producao": production_setup_to_text,
    "6_set_covering": set_covering_to_text,
    "7_tsp": tsp_to_text,
    "8_facility_location": facility_location_to_text,
    "9_cutting_stock": cutting_stock_to_text,
    "10_timetabling": timetabling_to_text,
}

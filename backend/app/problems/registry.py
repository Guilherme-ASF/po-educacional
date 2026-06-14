from __future__ import annotations

import copy
from typing import Any, Callable

from app.models.problem import ProblemModel
from app.problems import (
    bin_packing,
    cutting_stock,
    facility_location,
    knapsack_md,
    multiprocessor,
    production_setup,
    project_selection,
    set_covering,
    timetabling,
    tsp,
)

ProblemBuilder = Callable[[dict[str, Any]], ProblemModel]

MMOL_PROBLEMS: dict[str, dict[str, Any]] = {
    "1_multiprocessador": {
        "id": 1,
        "titulo": "Alocação de Tarefas em Sistema Multiprocessador",
        "tipo": "PLIP",
        "metodo_sugerido": "Branch and Bound",
        "builder": multiprocessor.build_model,
        "instancia_padrao": multiprocessor.DEFAULT_INSTANCE,
    },
    "2_selecao_projetos": {
        "id": 2,
        "titulo": "Seleção de Projetos de Pesquisa",
        "tipo": "PIB",
        "metodo_sugerido": "Branch and Bound",
        "builder": project_selection.build_model,
        "instancia_padrao": project_selection.DEFAULT_INSTANCE,
    },
    "3_knapsack_multidimensional": {
        "id": 3,
        "titulo": "Seleção de Fluxos em Datacenter (Knapsack MD)",
        "tipo": "PIB",
        "metodo_sugerido": "Branch and Bound",
        "builder": knapsack_md.build_model,
        "instancia_padrao": knapsack_md.DEFAULT_INSTANCE,
    },
    "4_bin_packing": {
        "id": 4,
        "titulo": "Escalonamento de VMs (Bin Packing)",
        "tipo": "PLIP",
        "metodo_sugerido": "Branch and Bound",
        "builder": bin_packing.build_model,
        "instancia_padrao": bin_packing.DEFAULT_INSTANCE,
    },
    "5_setup_producao": {
        "id": 5,
        "titulo": "Planejamento de Produção com Setup",
        "tipo": "PLIM",
        "metodo_sugerido": "Branch and Bound",
        "builder": production_setup.build_model,
        "instancia_padrao": production_setup.DEFAULT_INSTANCE,
    },
    "6_set_covering": {
        "id": 6,
        "titulo": "Cobertura de Zonas (Set Covering)",
        "tipo": "PIB",
        "metodo_sugerido": "Branch and Bound",
        "builder": set_covering.build_model,
        "instancia_padrao": set_covering.DEFAULT_INSTANCE,
    },
    "7_tsp": {
        "id": 7,
        "titulo": "Roteamento de Robô (TSP)",
        "tipo": "PLIP",
        "metodo_sugerido": "Branch and Cut",
        "builder": tsp.build_model,
        "instancia_padrao": tsp.DEFAULT_INSTANCE,
    },
    "8_facility_location": {
        "id": 8,
        "titulo": "Localização de Servidores CDN",
        "tipo": "PLIM",
        "metodo_sugerido": "Branch and Bound",
        "builder": facility_location.build_model,
        "instancia_padrao": facility_location.DEFAULT_INSTANCE,
    },
    "9_cutting_stock": {
        "id": 9,
        "titulo": "Empacotamento de Registros (Cutting Stock)",
        "tipo": "PLIM",
        "metodo_sugerido": "Branch and Bound",
        "builder": cutting_stock.build_model,
        "instancia_padrao": cutting_stock.DEFAULT_INSTANCE,
    },
    "10_timetabling": {
        "id": 10,
        "titulo": "Grade de Horários (Timetabling)",
        "tipo": "PLIM",
        "metodo_sugerido": "Branch and Cut",
        "builder": timetabling.build_model,
        "instancia_padrao": timetabling.DEFAULT_INSTANCE,
    },
}


def list_problems() -> list[dict[str, Any]]:
    return [
        {
            "chave": key,
            "id": meta["id"],
            "titulo": meta["titulo"],
            "tipo": meta["tipo"],
            "metodo_sugerido": meta["metodo_sugerido"],
        }
        for key, meta in MMOL_PROBLEMS.items()
    ]


def get_problem(chave: str) -> dict[str, Any]:
    if chave not in MMOL_PROBLEMS:
        raise ValueError(f"Problema MMOL desconhecido: {chave}")
    return MMOL_PROBLEMS[chave]


def _instance_to_json(inst: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(inst)
    pts = out.get("pontuacoes")
    if isinstance(pts, dict):
        out["pontuacoes"] = {
            "|".join(k) if isinstance(k, tuple) else str(k): v for k, v in pts.items()
        }
    return out


def instance_to_json(inst: dict[str, Any]) -> dict[str, Any]:
    """Instância serializável em JSON (ex.: pontuacoes com chaves 'D|S|H')."""
    return _instance_to_json(inst)


def normalize_instance(dados: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(dados)
    pts = out.get("pontuacoes")
    if isinstance(pts, dict):
        parsed: dict[tuple[str, str, str], int] = {}
        for k, v in pts.items():
            if isinstance(k, str) and "|" in k:
                parts = k.split("|")
                if len(parts) == 3:
                    parsed[(parts[0], parts[1], parts[2])] = int(v)
            elif isinstance(k, (list, tuple)) and len(k) == 3:
                parsed[(str(k[0]), str(k[1]), str(k[2]))] = int(v)
            elif isinstance(k, tuple) and len(k) == 3:
                parsed[k] = int(v)
        out["pontuacoes"] = parsed
    return out


def get_instance_json(chave: str) -> dict[str, Any]:
    meta = get_problem(chave)
    return instance_to_json(meta["instancia_padrao"])


def build_model(chave: str, dados: dict[str, Any] | None = None) -> ProblemModel:
    meta = get_problem(chave)
    payload = dados if dados is not None else meta["instancia_padrao"]
    payload = normalize_instance(payload)
    return meta["builder"](payload)

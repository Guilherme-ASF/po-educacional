from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.orchestrator import solve_educational, solve_mmol
from app.problems.registry import build_model, get_instance_json, list_problems
from app.parsers.input_parser import detect_input_format, parse_problem
from app.pedagogical.formatter import model_to_latex, model_to_text
from app.problems.mmol_text import mmol_to_text

app = FastAPI(
    title="PO Educacional API",
    description="Sistema educacional de Pesquisa Operacional",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://rare-adventure-production-e8d7.up.railway.app",
        "https://po-educacional-production-5497.up.railway.app",
        "http://localhost:5173",
        "http://localhost:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_VERSION = "1.0.0"


@app.get("/")
def root():
    return {
        "nome": "Sistema Educacional de Pesquisa Operacional",
        "versao": API_VERSION,
        "areas": ["PL", "PLI", "MMOL", "Branch and Bound", "Branch and Cut"],
    }


@app.get("/api/mmol/problems")
def mmol_list():
    return {"problemas": list_problems()}


@app.get("/api/mmol/instance/{chave}")
def mmol_instance(chave: str):
    try:
        return {"chave": chave, "instancia": get_instance_json(chave)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/mmol/model")
def mmol_model(body: dict):
    chave = body.get("problema")
    if not chave:
        raise HTTPException(status_code=422, detail="Campo 'problema' obrigatório")
    dados = body.get("dados")
    try:
        inst = dados if dados is not None else get_instance_json(chave)
        problem = build_model(chave, inst)
        try:
            texto = mmol_to_text(chave, inst)
        except ValueError:
            texto = model_to_text(problem)
        return {"chave": chave, "texto": texto, "latex": model_to_latex(problem)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")


@app.post("/api/mmol/solve")
def mmol_solve(body: dict):
    chave = body.get("problema")
    if not chave:
        raise HTTPException(status_code=422, detail="Campo 'problema' obrigatório")
    dados = body.get("dados")
    method = body.get("method")
    input_text = body.get("input_text")
    ga_params = body.get("ga_params") or {}
    try:
        result = solve_mmol(chave, dados, method, input_text, ga_params)
        result["api_versao"] = API_VERSION
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")


@app.get("/api/version")
def version():
    return {
        "versao": API_VERSION,
        "correcoes": [
            "Método gráfico com passos e SVG",
            "Parser e diagnóstico automático",
        ],
    }


@app.post("/api/parse")
def parse_input(body: dict):
    text = body.get("input_text", "")
    if len(text) < 3:
        raise HTTPException(status_code=422, detail="input_text muito curto")
    try:
        fmt = detect_input_format(text)
        problem = parse_problem(text)
        return {
            "formato_detectado": fmt,
            "latex": model_to_latex(problem),
            "modelo": problem.model_dump(),
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/solve")
def solve(body: dict):
    text = body.get("input_text", "")
    method = body.get("method")
    ga_params = body.get("ga_params") or {}
    if len(text) < 3:
        raise HTTPException(status_code=422, detail="input_text muito curto")
    try:
        result = solve_educational(text, method, ga_params)
        result["api_versao"] = API_VERSION
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")

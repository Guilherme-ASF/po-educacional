from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.orchestrator import solve_educational
from app.parsers.input_parser import detect_input_format, parse_problem
from app.pedagogical.formatter import model_to_latex

app = FastAPI(
    title="PO Educacional API",
    description="Sistema educacional de Pesquisa Operacional",
    version="0.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_VERSION = "0.5.0"


@app.get("/")
def root():
    return {
        "nome": "Sistema Educacional de Pesquisa Operacional",
        "versao": API_VERSION,
        "areas": ["PL", "Simplex", "Dualidade", "Método Gráfico"],
    }


@app.get("/api/version")
def version():
    return {
        "versao": API_VERSION,
        "correcoes": [
            "Dualidade forte/fraca com painel primal-dual",
            "Simplex pedagógico (versão anterior)",
            "Método gráfico para PL 2D",
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
    if len(text) < 3:
        raise HTTPException(status_code=422, detail="input_text muito curto")
    try:
        result = solve_educational(text, method)
        result["api_versao"] = API_VERSION
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")

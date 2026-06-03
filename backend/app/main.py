from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.diagnostic.analyzer import diagnose
from app.parsers.input_parser import detect_input_format, parse_problem
from app.pedagogical.formatter import interpret_problem, model_to_latex

app = FastAPI(
    title="PO Educacional API",
    description="Sistema educacional de Pesquisa Operacional",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_VERSION = "0.2.0"


@app.get("/api/version")
def version():
    return {"versao": API_VERSION}


@app.post("/api/parse")
def parse_input(body: dict):
    text = body.get("input_text", "")
    if len(text) < 3:
        raise HTTPException(status_code=422, detail="input_text muito curto")
    try:
        fmt = detect_input_format(text)
        problem = parse_problem(text)
        diagnostic = diagnose(problem)
        return {
            "formato_detectado": fmt,
            "latex": model_to_latex(problem),
            "modelo": problem.model_dump(),
            "diagnostico": diagnostic,
            "interpretacao": interpret_problem(problem),
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/solve")
def solve(_body: dict):
    raise HTTPException(
        status_code=501,
        detail="Resolução pedagógica em desenvolvimento (próxima versão: método gráfico).",
    )

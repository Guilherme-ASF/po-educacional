from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="PO Educacional API",
    description="Sistema educacional de Pesquisa Operacional",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_VERSION = "0.1.0"


@app.get("/")
def root():
    return {
        "nome": "Sistema Educacional de Pesquisa Operacional",
        "versao": API_VERSION,
        "status": "em_construcao",
    }


@app.get("/api/version")
def version():
    return {"versao": API_VERSION}


class SolveRequest(BaseModel):
    input_text: str
    method: str | None = None


@app.post("/api/solve")
def solve(_body: SolveRequest):
    return {
        "mensagem": "Resolução pedagógica em desenvolvimento.",
        "versao": API_VERSION,
    }

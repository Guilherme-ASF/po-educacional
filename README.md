# PO Educacional — Branch-and-Bound para PLI

Sistema web educacional de Pesquisa Operacional (UFERSA/UERN — MMOL), com **Simplex próprio**, **Branch-and-Bound** e interface gráfica da árvore de decisão.

## Requisitos

- Python 3.11+
- Node.js 18+
- npm

## Instalação

### Backend

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Acesse **http://localhost:5173**

## Execução

1. Cole o problema no campo de texto (formato matemático).
2. Escolha o método (**Branch and Bound** para variáveis inteiras).
3. Clique em **Resolver**.
4. Na árvore B&B, **clique em um nó** para ver o tableau do subproblema.

### API

```http
POST http://localhost:8001/api/solve
Content-Type: application/json

{
  "input_text": "Max Z = 8x1 + 5x2\n...",
  "method": "Branch and Bound"
}
```

A resposta inclui `4_resolucao.branch_and_bound.desempenho` com `nos_explorados`, `nos_total` e `tempo_ms`.

### Lista MMOL (10 problemas)

Na interface, ative **Problema da lista (10 modelos)** na barra lateral ou use a API:

```http
GET  http://localhost:8001/api/mmol/problems
POST http://localhost:8001/api/mmol/solve
Content-Type: application/json

{ "problema": "6_set_covering", "method": "Branch and Bound" }
```

```powershell
python tests/run_mmol.py
```

Detalhes e Z* esperados em `docs/COMPATIBILIDADE_LISTA_MMOL.md`.

## Casos de teste reproduzíveis

| ID | Arquivo | Método | Z* esperado |
|----|---------|--------|-------------|
| caso1 | `tests/casos/caso1_plip_enunciado.txt` | Branch and Bound | 40 |
| caso2 | `tests/casos/caso2_pl_continuo.txt` | Método Gráfico | 9 |
| caso3 | `tests/casos/caso3_plip_maior.txt` | Branch and Bound | 42 |

```powershell
cd backend
venv\Scripts\activate
python ..\tests\run_casos.py
```

Resultados em `tests/resultados_casos.json`.

## Estrutura do projeto

```
backend/app/
  parsers/          # Entrada textual → modelo
  solvers/          # Simplex, B&B, B&C (Gomory), gráfico
  orchestrator.py   # Orquestração pedagógica
frontend/src/       # Interface React
tests/casos/        # Instâncias documentadas
report/relatorio.md # Modelo do relatório técnico (exportar para PDF)
docs/               # Roadmap e compatibilidade com a lista MMOL
```

## Relatório técnico

Modelo em `report/relatorio.md` (máx. 8 páginas em PDF). Exporte com Pandoc, Word ou imprima do editor Markdown.

## Licença e autoria

PPGCC — UFERSA. Repositório: [Guilherme-ASF/po-educacional](https://github.com/Guilherme-ASF/po-educacional)

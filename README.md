# PO Educacional v1.0

Sistema web educacional de **Pesquisa Operacional** (PPGCC — UFERSA/UERN), desenvolvido para a disciplina **Modelos e Métodos de Otimização Linear (MMOL)**.

Inclui **Simplex pedagógico**, **Branch and Bound** interativo, **Branch and Cut (Gomory)**, **dualidade**, **método gráfico**, **algoritmo genético** e os **10 problemas clássicos da lista MMOL** com modelagem compacta comentada (`∀`, `Σ`, `@dados`, `@modelo`).

Repositório: [Guilherme-ASF/po-educacional](https://github.com/Guilherme-ASF/po-educacional)

---

## Funcionalidades (v1.0)

| Área | Recursos |
|------|----------|
| **Entrada** | PL/PLI em texto, linguagem natural, DSL compacto MMOL |
| **Métodos** | Simplex, gráfico (2 vars), relaxação LP, B&B, B&C, Gomory, dualidade, GA |
| **B&B / B&C** | Árvore com pan/zoom; tableau por nó; cortes de Gomory comentados |
| **MMOL** | 10 problemas com instância padrão, modelagem pedagógica e Z* validados |
| **API** | FastAPI REST — `/api/solve`, `/api/mmol/*` |

---

## Requisitos

- **Python** 3.11+
- **Node.js** 18+ e npm

---

## Instalação e execução

### 1. Backend (porta 8001)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### 2. Frontend (porta 5173)

```powershell
cd frontend
npm install
npm run dev
```

Abra **http://localhost:5173** (o Vite faz proxy para a API em `8001`).

---

## Uso rápido

### Modo livre (PL / PLI)

1. Cole o problema no editor (ou use linguagem natural).
2. Escolha o método (ex.: **Branch and Bound** para inteiros).
3. Clique em **Resolver**.
4. Na árvore B&B, **clique em um nó** para ver o tableau da relaxação.

### Modo MMOL (10 problemas)

1. Marque **Problema da lista (10 modelos)** na barra lateral.
2. Selecione o problema (1–10).
3. A modelagem compacta comentada carrega automaticamente.
4. Escolha o método sugerido ou outro compatível e resolva.

O **Guia de modelagem** acima do editor explica símbolos: `∀`, `Σ`, `x[t,s]`, `p(t,s)`, `@dados`, etc.

---

## Política de solvers (regras MMOL)

Conforme o enunciado do trabalho:

| Permitido | Uso no projeto |
|-----------|----------------|
| **numpy** | Álgebra linear (ex.: vértices, manipulação de tableau) |
| **scipy.optimize.linprog** | Apenas **relaxações LP** (subproblemas contínuos no B&B/B&C) |
| **Simplex pedagógico próprio** | Tableau passo a passo, dualidade |
| **B&B / B&C próprios** | Solução principal de PLI/PLIB |
| **Algoritmos dedicados** | Enumeração / DP nos problemas 1, 4, 7, 9, 10 |

| **Não permitido** | Status |
|-------------------|--------|
| CPLEX, Gurobi, OR-Tools, GLPK como caixa-preta para PLI | Não utilizado |
| Solver MIP comercial integrado | Não utilizado |

O **Z*** de problemas inteiros vem do **B&B**, **B&C** ou **solver dedicado** documentado — nunca de solver de PLI externo.

---

## Lista MMOL — instâncias e Z* esperados

| # | Chave | Método sugerido | Z* (instância padrão) |
|---|--------|-----------------|------------------------|
| 1 | `1_multiprocessador` | Branch and Bound | 7 |
| 2 | `2_selecao_projetos` | Branch and Bound | 420 |
| 3 | `3_knapsack_multidimensional` | Branch and Bound | 165 |
| 4 | `4_bin_packing` | Branch and Bound | 3 |
| 5 | `5_setup_producao` | Branch and Bound | 490 |
| 6 | `6_set_covering` | Branch and Bound | 230 |
| 7 | `7_tsp` | Branch and Cut | 70 |
| 8 | `8_facility_location` | Branch and Bound | 53 |
| 9 | `9_cutting_stock` | Branch and Bound | 9 |
| 10 | `10_timetabling` | Branch and Cut | 36 |

Validação automatizada:

```powershell
cd backend
.\venv\Scripts\activate
python ..\tests\run_mmol.py
python ..\tests\run_casos.py
```

---

## API REST

### Resolver problema livre

```http
POST http://localhost:8001/api/solve
Content-Type: application/json

{
  "input_text": "Max Z = 8x1 + 5x2\n...",
  "method": "Branch and Bound"
}
```

### MMOL

```http
GET  http://localhost:8001/api/mmol/problems
POST http://localhost:8001/api/mmol/model
POST http://localhost:8001/api/mmol/solve

{ "problema": "4_bin_packing", "method": "Branch and Bound" }
```

Resposta pedagógica estruturada: `1_identificacao` … `8_conclusao`. B&B inclui `4_resolucao.branch_and_bound.nos` (árvore) e `desempenho`.

---

## Estrutura do projeto

```
backend/app/
  parsers/           # Entrada textual, DSL, expansão Σ
  problems/          # 10 builders MMOL + mmol_text (modelagem compacta)
  solvers/           # Simplex, B&B, B&C, gráfico, GA, scipy LP
  orchestrator.py    # Fluxo pedagógico unificado
frontend/src/
  components/        # BranchBoundTree, ModelingGuide, SolutionReport, …
tests/               # run_mmol.py, run_casos.py, casos/
report/relatorio.md  # Modelo do relatório técnico (PDF)
docs/                # Compatibilidade MMOL
```

---

## Relatório técnico

Modelo em `report/relatorio.md` (máx. 8 páginas em PDF). Exporte com Pandoc, Word ou imprima do editor Markdown.

---

## Versão e histórico

- **v1.0.0** — Release completo: 10 problemas MMOL, modelagem compacta, B&B/B&C interativo, dualidade, GA, testes.
- Tags anteriores `v0.1.0` … `v0.8.0` documentam a evolução incremental no GitHub.

---

## Licença e autoria

PPGCC — UFERSA. Autor: Guilherme ASF.

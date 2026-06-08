# PO Educacional — v0.5.0 (Dualidade)

Sistema web para ensinar Pesquisa Operacional com **método gráfico**, **Simplex pedagógico** e **painel primal-dual** (dualidade forte/fraca).

## O que funciona nesta versão

- Parser e diagnóstico automático (v0.2+)
- Método gráfico para PL com 2 variáveis (v0.3+)
- Tableau Simplex passo a passo com frações (v0.4+)
- **Novo:** formulação dual, resolução do dual e classificação de dualidade forte/fraca
- Painel comparativo primal × dual na interface

## Instalação

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
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

## Uso

1. Cole um problema PL no formato matemático.
2. Escolha **Dualidade** para ver o painel primal-dual completo, ou **Simplex** / **Método Gráfico**.
3. O relatório inclui o painel de dualidade mesmo quando outro método é o principal.

## Próximas versões

- v0.6.0 — Relaxação linear e Branch and Bound (PLI)
- v0.7.0 — Branch and Cut e Algoritmo Genético
- v0.8.0 — Lista MMOL, logo PPGCC e documentação final

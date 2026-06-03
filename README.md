# PO Educacional (em construção)

Sistema web para ensinar Pesquisa Operacional — **versão inicial (esqueleto)**.

## O que funciona nesta versão

- API FastAPI com rota de status (`GET /api/version`)
- Interface React com campo de texto e botão (resolução ainda não implementada)

## Instalação

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Acesse http://localhost:5173

## Próximos passos

- Parser de entrada (formato matemático e simplificado)
- Diagnóstico automático do tipo de problema

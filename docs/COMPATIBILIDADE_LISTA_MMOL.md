# Compatibilidade com a Lista MMOL (10 problemas)

Sistema validado contra as instâncias padrão em `backend/app/problems/`.

## Modelagem na interface

Problemas **1–10** exibem formulação **compacta comentada** (`@dados` + `@modelo` + `∀`/`Σ`).

O problema **1** permite editar `@dados` (tempos `p(t,s)` e capacidade `C`); os demais usam instância padrão via builder Python.

## Z* esperados

| ID | Problema | Z* |
|----|----------|-----|
| 1 | Multiprocessador | 7 |
| 2 | Seleção de projetos | 420 |
| 3 | Knapsack multidimensional | 165 |
| 4 | Bin packing | 3 |
| 5 | Setup produção | 490 |
| 6 | Set covering | 230 |
| 7 | TSP | 70 |
| 8 | Facility location | 53 |
| 9 | Cutting stock | 9 |
| 10 | Timetabling | 36 |

## Testes

```powershell
python tests/run_mmol.py
```

## Solvers por problema

| Problema | Solver principal (método ≠ B&B) | B&B / B&C |
|----------|----------------------------------|-----------|
| 1 | Enumeração makespan | Árvore completa |
| 4 | Busca exata em bins | Árvore |
| 7 | TSP exato (enumeração) | B&C + árvore |
| 9 | DP / padrões | B&C + fallback B&B |
| 10 | Enumeração grades | B&C |

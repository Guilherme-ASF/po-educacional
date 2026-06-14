# Relatório Técnico — PLIP com Branch-and-Bound

**Disciplina:** Métodos e Modelos de Otimização Linear  
**Equipe:** [preencher]  
**Problema abordado:** Programação Linear Inteira (modelo genérico / instância tipo enunciado PLIP)

---

## a) Formulação matemática

### Variáveis

- \(x_j \in \mathbb{Z}_{\geq 0}\) — níveis das variáveis de decisão (ex.: \(x_1, x_2\)).

### Função objetivo

\[
\max Z = 8x_1 + 5x_2
\]

### Restrições

\[
\begin{aligned}
x_1 + x_2 &\leq 6 \\
9x_1 + 5x_2 &\leq 45 \\
x_1, x_2 &\geq 0 \\
x_1, x_2 &\in \mathbb{Z}
\end{aligned}
\]

**Modelo relaxado (cada nó B&B):** substitui-se \(x_j \in \mathbb{Z}\) por \(x_j \in \mathbb{R}_{\geq 0}\) e adicionam-se cortes de ramificação \(x_k \leq \lfloor v_k \rfloor\) ou \(x_k \geq \lceil v_k \rceil\).

---

## b) Estratégia de Branch-and-Bound

1. **Relaxação:** enumeração de vértices (até 8 variáveis) ou Simplex.
2. **Ramificação:** *first fractional* — primeira variável inteira com parte fracionária máxima.
3. **Poda:** (i) inviabilidade do subproblema; (ii) dominância quando \(Z_{relax}\) não supera o incumbent; (iii) solução inteira factível atualiza incumbent.
4. **Busca:** FIFO (fila de nós).
5. **Dedup:** consolidação de limites \(x_j \leq u\) e \(x_j \geq \ell\) para evitar subproblemas repetidos.

---

## c) Exemplos de execução

### Instância 1 — Enunciado (2 variáveis)

| Campo | Valor |
|-------|-------|
| \(x_1^*, x_2^*\) | 5, 0 |
| \(Z^*\) | 40 |
| Nós explorados | 7 |
| Tempo | ~2 ms |

Relaxação raiz: \(Z=41{,}25\), \((3{,}75; 2{,}25)\) → ramificação em \(x_1\).

### Instância 2 — PL contínua (validação gráfica)

`tests/casos/caso2_pl_continuo.txt` — \(Z^*=9\), \((1;3)\).

### Instância 3 — 3 variáveis inteiras

`tests/casos/caso3_plip_maior.txt` — \(Z^*=42\), \((1;4;0)\).

---

## d) Análise de desempenho

| Instância | Variáveis | Restrições | Nós | Tempo (ms) | \(Z^*\) |
|-----------|-----------|------------|-----|------------|--------|
| caso1 | 2 | 2 | 7 | 1,9 | 40 |
| caso3 | 3 | 3 | 1* | 1,2 | 42 |

\* caso3 resolve na raiz com solução inteira após relaxação.

**Qualidade:** soluções exatas (otimalidade garantida pelo B&B).  
**Limitação:** instâncias com muitas variáveis binárias ou modelos de atribuição exigem implementação específica (Problemas 1–10 da lista completa).

---

## Repositório e testes

```powershell
python tests/run_casos.py
```

Interface: http://localhost:5173 — método **Branch and Bound**, árvore interativa com tableau por nó.

---

*Exportar este arquivo para PDF (máx. 8 páginas) antes da entrega no SIGAA.*

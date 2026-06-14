# Publicação gradual no GitHub — comandos passo a passo

Este guia publica o **PO Educacional** em **8 versões**, sem subir o projeto completo de uma vez.

**Regra de ouro:** nunca use `git add .` até a **v0.8.0**. Cada versão adiciona só os arquivos listados no manifest.

**Nota:** nas versões **v0.1** e **v0.2** o backend usa arquivos “enxutos” (overlays). A partir da **v0.3** entra o `orchestrator.py` completo; o repositório só fica 100% executável quando todos os solvers forem publicados (**v0.7**). Isso é intencional para o histórico gradual.

---

## Versões

| Versão | Foco | O que o usuário vê |
|--------|------|-------------------|
| **v0.1.0** | Esqueleto | API “hello”, React vazio, README mínimo |
| **v0.2.0** | Modelo + parser | Colar problema, ver LaTeX e diagnóstico |
| **v0.3.0** | Método gráfico | Resolver PL 2D com passos e SVG |
| **v0.4.0** | Simplex | Tableau passo a passo, frações |
| **v0.5.0** | Dualidade | Painel primal/dual |
| **v0.6.0** | PLI básico | Relaxação linear + Branch and Bound |
| **v0.7.0** | Avançado | Branch and Cut + Algoritmo Genético |
| **v0.8.0** | Acabamento | Logo PPGCC, GitHub, README e scripts |

---

## Pré-requisitos

- [Git](https://git-scm.com/) instalado
- Conta GitHub: [Guilherme-ASF](https://github.com/Guilherme-ASF)
- (Opcional) [GitHub CLI](https://cli.github.com/): `gh auth login`

Abra o PowerShell na pasta do projeto:

```powershell
cd "c:\Users\Guilherme\Desktop\Otimização"
```

---

## Passo 0 — Backup e preparação (uma vez)

**Antes de cada publicação**, sincronize o staging com o projeto completo local:

```powershell
.\scripts\sync-staging.ps1
```

Isso grava cópias em `_staging/` (para o GitHub) e `_dev_snapshot/` (para restaurar seu PC após publicar).

Na **primeira vez** (v0.1.0), aplique o esqueleto:

```powershell
.\scripts\preparar-repositorio.ps1
.\scripts\sync-staging.ps1
```

---

## Passo 1 — Criar repositório no GitHub

**Opção A — pelo site**

1. Acesse https://github.com/new  
2. Nome: `po-educacional` (ou outro)  
3. **Não** marque “Add a README”  
4. Crie o repositório vazio  

**Opção B — GitHub CLI**

```powershell
gh repo create po-educacional --public --description "Sistema web para ensinar Pesquisa Operacional passo a passo"
```

---

## Passo 2 — Publicar v0.1.0 (esqueleto)

```powershell
git init
git branch -M main

.\scripts\publicar-versao.ps1 -Versao v0.1.0

git remote add origin https://github.com/Guilherme-ASF/po-educacional.git
git push -u origin main
git push origin v0.1.0
```

> Se o remoto já existir, use:  
> `git remote set-url origin https://github.com/Guilherme-ASF/po-educacional.git`

**O que sobe no GitHub:** só os arquivos de `scripts/manifests/v0.1.0.txt` (API stub, React mínimo, README “em construção”).

---

## Passo 3 — Publicar v0.2.0 (parser + diagnóstico)

Espere alguns dias (recomendado: 3–7) e execute:

```powershell
.\scripts\publicar-versao.ps1 -Versao v0.2.0 -Push
```

---

## Passo 4 — Publicar v0.3.0 (método gráfico)

```powershell
.\scripts\publicar-versao.ps1 -Versao v0.3.0 -Push
```

---

## Passo 5 — Publicar v0.4.0 (Simplex)

```powershell
.\scripts\publicar-versao.ps1 -Versao v0.4.0 -Push
```

---

## Passo 6 — Publicar v0.5.0 (dualidade)

```powershell
.\scripts\publicar-versao.ps1 -Versao v0.5.0 -Push
```

---

## Passo 7 — Publicar v0.6.0 (PLI — B&B)

```powershell
.\scripts\publicar-versao.ps1 -Versao v0.6.0 -Push
```

---

## Passo 8 — Publicar v0.7.0 (cortes + genético)

```powershell
.\scripts\publicar-versao.ps1 -Versao v0.7.0 -Push
```

---

## Passo 9 — Publicar v0.8.0 (logo, GitHub, docs)

```powershell
.\scripts\publicar-versao.ps1 -Versao v0.8.0 -Push
```

---

## Resumo — todos os comandos em sequência

```powershell
cd "c:\Users\Guilherme\Desktop\Otimização"

# 0) Preparar (uma vez)
.\scripts\preparar-repositorio.ps1

# 1) v0.1.0 — primeiro push
git init
git branch -M main
.\scripts\publicar-versao.ps1 -Versao v0.1.0
git remote add origin https://github.com/Guilherme-ASF/po-educacional.git
git push -u origin main
git push origin v0.1.0

# 2) Demais versões (espere dias entre cada uma)
.\scripts\publicar-versao.ps1 -Versao v0.2.0 -Push
.\scripts\publicar-versao.ps1 -Versao v0.3.0 -Push
.\scripts\publicar-versao.ps1 -Versao v0.4.0 -Push
.\scripts\publicar-versao.ps1 -Versao v0.5.0 -Push
.\scripts\publicar-versao.ps1 -Versao v0.6.0 -Push
.\scripts\publicar-versao.ps1 -Versao v0.7.0 -Push
.\scripts\publicar-versao.ps1 -Versao v0.8.0 -Push
```

---

## O que cada script faz

| Script | Função |
|--------|--------|
| `preparar-repositorio.ps1` | Grava cópia completa em `_staging/`; aplica overlay da v0.1.0 |
| `publicar-versao.ps1` | Restaura do `_staging` só os arquivos do manifest; `git add` **apenas** esses caminhos; commit + tag |

Parâmetro **`-Push`**: envia `main` e a tag para o GitHub após o commit.

Mensagem de commit personalizada:

```powershell
.\scripts\publicar-versao.ps1 -Versao v0.3.0 -Mensagem "feat: grafico com SVG da regiao factivel" -Push
```

---

## Conferir o que será publicado (antes do push)

```powershell
git status
git show --stat HEAD
git ls-tree -r HEAD --name-only
```

Na **v0.1.0** você **não** deve ver `simplex.py`, `dual.py`, `DualPanel.tsx`, etc.

---

## Release no GitHub (opcional)

Após cada tag:

```powershell
gh release create v0.3.0 --title "v0.3.0 — Método gráfico" --notes "Interseção de retas, vértices factíveis e SVG."
```

---

## O que não sobe no GitHub

- `backend/venv/`
- `frontend/node_modules/`
- `_staging/` (backup local)
- `assets/` (imagens temporárias do Cursor)

---

## Problemas comuns

### `remote: Repository not found`

O repositório **ainda não existe** no GitHub (ou o nome está errado). Crie antes do push:

**No site:** https://github.com/new → nome `po-educacional` → **sem** README → Create.

**Ou com GitHub CLI:**

```powershell
gh auth login
gh repo create po-educacional --public --source=. --remote=origin
```

Se já configurou `origin` com URL errada:

```powershell
git remote remove origin
git remote add origin https://github.com/Guilherme-ASF/po-educacional.git
```

### `unable to sign the tag` / `Couldn't get agent socket`

O commit foi criado, mas a **tag não**. Crie manualmente e envie:

```powershell
git tag -f v0.1.0
git push -u origin main
git push origin v0.1.0
```

(O script `publicar-versao.ps1` já usa tag leve, sem assinatura GPG.)

### `src refspec v0.1.0 does not match any`

A tag não existe (falha de assinatura acima). Rode `git tag -f v0.1.0` e tente o push da tag de novo.

**`Manifest nao encontrado`**  
Use o nome exato: `v0.2.0` (com `v` e três números).

**`remoto nao configurado`**  
Configure antes:  
`git remote add origin https://github.com/Guilherme-ASF/SEU-REPO.git`

**Arquivo nao encontrado no add**  
Rode `.\scripts\sync-staging.ps1` para recriar o `_staging/`.

### Depois de publicar, local volta para v0.2 / botao desabilitado

O script `publicar-versao.ps1` copia arquivos **antigos** do staging para a pasta de trabalho antes do commit. **Sempre rode antes:**

```powershell
.\scripts\sync-staging.ps1
```

Depois de publicar, o script restaura automaticamente de `_dev_snapshot/`. Se precisar manualmente:

```powershell
.\scripts\restaurar-desenvolvimento.ps1
```

### Corrigir v0.3.0 ja publicada no GitHub (main ainda em 0.2.0)

```powershell
.\scripts\sync-staging.ps1
.\scripts\publicar-versao.ps1 -Versao v0.3.0 -Mensagem "fix: API 0.3.0 e resolucao grafica" -Push
```

(O overlay `scripts/overlays/v0.3.0/` agora traz `main.py` e `App.tsx` corretos.)

**Quero continuar desenvolvendo localmente**  
O projeto completo continua na sua pasta; o `_staging/` guarda a versão final para as próximas publicações. Após editar código, copie de novo para `_staging` se necessário:

```powershell
.\scripts\preparar-repositorio.ps1
```

(Isso reaplica o overlay v0.1.0 — faça isso só se ainda não tiver publicado a v0.1.0, ou copie manualmente os arquivos alterados para `_staging/`.)

---

## Lista de manifests

Os caminhos exatos de cada versão estão em:

- `scripts/manifests/v0.1.0.txt` … `v0.8.0.txt`

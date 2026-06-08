import { useEffect, useState } from 'react'
import { SolutionReport } from './components/SolutionReport'
import ppgccLogo from './images/PPgCC-LOGO.png'
import './App.css'

function GitHubIcon() {
  return (
    <svg
      className="github-icon"
      viewBox="0 0 24 24"
      aria-hidden="true"
      fill="currentColor"
    >
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.36-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
    </svg>
  )
}

const EXAMPLES = {
  matematico: `Max Z = 2x1 + 3x2

S.A.

x1 + x2 <= 6
2x1 + 3x2 >= 10

x1, x2 >= 0`,

  pli: `Max Z = 2x1 + 3x2

S.A.

x1 + x2 <= 6
2x1 + 3x2 >= 10

x1, x2 >= 0
x1, x2 inteiro`,

  simplificado: `Z = x1*2 + x2*3

S.A.

x1 + x2 <= 6

x1*2 + x2*3 >= 10

x1,x2 >= 0`,

  natural: `Desejo maximizar o lucro.

Cada produto A gera lucro de 2.
Cada produto B gera lucro de 3.

Posso produzir no máximo 6 unidades somadas.

Preciso produzir pelo menos 10 unidades ponderadas.

As variáveis são não negativas.`,
}

const METHODS = [
  { value: '', label: 'Automático' },
  { value: 'Método Gráfico', label: 'Método Gráfico' },
  { value: 'Simplex', label: 'Simplex' },
  { value: 'Dualidade', label: 'Dualidade' },
  { value: 'Relaxação Linear', label: 'Relaxação Linear' },
  { value: 'Branch and Bound', label: 'Branch and Bound' },
  { value: 'Branch and Cut', label: 'Branch and Cut' },
  { value: 'Planos de Corte (Gomory)', label: 'Planos de Corte (Gomory)' },
  { value: 'Algoritmo Genético', label: 'Algoritmo Genético' },
]

export default function App() {
  const [input, setInput] = useState(EXAMPLES.matematico)
  const [method, setMethod] = useState('')
  const [populacao, setPopulacao] = useState(20)
  const [geracoes, setGeracoes] = useState(30)
  const [mutacao, setMutacao] = useState(0.15)
  const [cruzamento, setCruzamento] = useState(0.8)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [apiVersion, setApiVersion] = useState<string | null>(null)
  const [apiStatus, setApiStatus] = useState<'loading' | 'ok' | 'erro'>('loading')

  const showGaParams = method === 'Algoritmo Genético' || method === ''

  useEffect(() => {
    fetch('/api/version')
      .then((r) => {
        if (!r.ok) throw new Error('offline')
        return r.json()
      })
      .then((j) => {
        setApiVersion(String(j.versao ?? ''))
        setApiStatus('ok')
      })
      .catch(() => {
        setApiVersion(null)
        setApiStatus('erro')
      })
  }, [])

  async function handleSolve() {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/solve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          input_text: input,
          method: method || null,
          ga_params: {
            populacao,
            geracoes,
            mutacao,
            cruzamento,
          },
        }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Erro ao resolver')
      setResult(json)
      if (json.api_versao) {
        setApiVersion(String(json.api_versao))
        setApiStatus('ok')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro desconhecido')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header>
        <div className="header-top">
          <a
            className="ppgcc-link"
            href="https://ppgcc.ufersa.edu.br/"
            target="_blank"
            rel="noopener noreferrer"
            title="Programa de Pós-Graduação em Ciência da Computação — UFERSA"
          >
            <img
              src={ppgccLogo}
              alt="PPGCC — Programa de Pós-Graduação em Ciência da Computação"
            />
          </a>
          <a
            className="github-link"
            href="https://github.com/Guilherme-ASF/po-educacional"
            target="_blank"
            rel="noopener noreferrer"
            title="GitHub — Guilherme Augusto Silva Freitas"
            aria-label="Perfil no GitHub"
          >
            <GitHubIcon />
            <span>Guilherme-ASF</span>
          </a>
        </div>
        <h1>PO Educacional</h1>
        <p>Sistema tutor de Pesquisa Operacional — PL, PLI, Simplex, Branch &amp; Bound e mais</p>
        <p className="api-version">
          {apiStatus === 'loading' && 'Conectando ao backend...'}
          {apiStatus === 'ok' && apiVersion && (
            <>Backend conectado — <strong>API v{apiVersion}</strong></>
          )}
          {apiStatus === 'erro' && (
            <span className="warn">
              Backend não encontrado. Inicie: uvicorn app.main:app --reload --port 8001
            </span>
          )}
        </p>
      </header>

      <main>
        <aside className="sidebar">
          <h3>Exemplos</h3>
          <button className="example-btn" onClick={() => setInput(EXAMPLES.matematico)}>
            PL — Formato Matemático
          </button>
          <button className="example-btn" onClick={() => setInput(EXAMPLES.pli)}>
            PLI — Variáveis inteiras
          </button>
          <button className="example-btn" onClick={() => setInput(EXAMPLES.simplificado)}>
            Formato Simplificado
          </button>
          <button className="example-btn" onClick={() => setInput(EXAMPLES.natural)}>
            Linguagem Natural
          </button>

          <h3>Método</h3>
          <select value={method} onChange={(e) => setMethod(e.target.value)}>
            {METHODS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>

          {showGaParams && (
            <div className="ga-params">
              <h3>Algoritmo Genético</h3>
              <label>
                População
                <input
                  type="number"
                  min={4}
                  max={200}
                  value={populacao}
                  onChange={(e) => setPopulacao(Number(e.target.value))}
                />
              </label>
              <label>
                Gerações
                <input
                  type="number"
                  min={1}
                  max={500}
                  value={geracoes}
                  onChange={(e) => setGeracoes(Number(e.target.value))}
                />
              </label>
              <label>
                Mutação (0–1)
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.05}
                  value={mutacao}
                  onChange={(e) => setMutacao(Number(e.target.value))}
                />
              </label>
              <label>
                Cruzamento (0–1)
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.05}
                  value={cruzamento}
                  onChange={(e) => setCruzamento(Number(e.target.value))}
                />
              </label>
            </div>
          )}
        </aside>

        <div className="workspace">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Digite o problema..."
            rows={14}
          />
          <button className="solve-btn" onClick={handleSolve} disabled={loading}>
            {loading ? 'Resolvendo...' : 'Resolver com explicação completa'}
          </button>
          {error && <div className="error">{error}</div>}
          {result && <SolutionReport data={result} />}
        </div>
      </main>
    </div>
  )
}

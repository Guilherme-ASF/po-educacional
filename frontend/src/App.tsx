import { useEffect, useState } from 'react'
import './App.css'

export default function App() {
  const [input, setInput] = useState('Max Z = 2x1 + 3x2\n\nx1 + x2 <= 6\nx1, x2 >= 0')
  const [apiVersion, setApiVersion] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/version')
      .then((r) => r.json())
      .then((j) => setApiVersion(String(j.versao ?? '')))
      .catch(() => setApiVersion(null))
  }, [])

  return (
    <div className="app">
      <header>
        <h1>PO Educacional</h1>
        <p>Sistema tutor de Pesquisa Operacional — versão inicial</p>
        {apiVersion && <p className="api-version">Backend conectado — API v{apiVersion}</p>}
      </header>
      <main>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Digite o problema..."
          rows={12}
        />
        <button type="button" className="solve-btn" disabled>
          Resolver (em breve)
        </button>
      </main>
    </div>
  )
}

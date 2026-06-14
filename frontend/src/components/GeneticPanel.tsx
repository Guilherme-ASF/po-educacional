import { useCallback, useEffect, useMemo, useState } from 'react'
import './GeneticPanel.css'

interface GAIndividual {
  cromossomo: number[]
  fitness: number
  factivel?: boolean
}

interface GAEvent {
  tipo: string
  [key: string]: unknown
}

interface GAGeneration {
  geracao: number
  populacao: GAIndividual[]
  melhor: { cromossomo: number[]; fitness: number }
  fitness_medio: number
  operacoes?: string[]
  eventos?: GAEvent[]
  stats?: { n_selecoes: number; n_cruzamentos: number; n_mutacoes: number }
}

interface Props {
  data: Record<string, unknown>
}

const CHART_W = 640
const CHART_H = 220
const PAD = { t: 20, r: 20, b: 36, l: 52 }

export function GeneticPanel({ data }: Props) {
  const geracoes = (data.geracoes as GAGeneration[]) ?? []
  const melhorGeracao = Number(data.melhor_geracao ?? 0)
  const melhor = data.melhor as { solucao?: Record<string, number>; fitness?: number }
  const params = data.parametros as Record<string, unknown> | undefined

  const [visibleCount, setVisibleCount] = useState(1)
  const [playing, setPlaying] = useState(true)
  const [speedMs, setSpeedMs] = useState(450)
  const [expandedGen, setExpandedGen] = useState<number | null>(null)

  const total = geracoes.length

  useEffect(() => {
    setVisibleCount(1)
    setPlaying(true)
    setExpandedGen(null)
  }, [geracoes])

  useEffect(() => {
    if (!playing || visibleCount >= total) {
      if (visibleCount >= total) setPlaying(false)
      return
    }
    const id = window.setTimeout(() => setVisibleCount((c) => c + 1), speedMs)
    return () => window.clearTimeout(id)
  }, [playing, visibleCount, total, speedMs])

  const visible = useMemo(
    () => geracoes.slice(0, visibleCount),
    [geracoes, visibleCount],
  )

  const yBounds = useMemo(() => {
    const vals = geracoes.flatMap((g) => [g.melhor.fitness, g.fitness_medio])
    const min = Math.min(...vals)
    const max = Math.max(...vals)
    const pad = (max - min) * 0.08 || 1
    return { min: min - pad, max: max + pad }
  }, [geracoes])

  const replay = useCallback(() => {
    setVisibleCount(1)
    setPlaying(true)
  }, [])

  const showAll = useCallback(() => {
    setVisibleCount(total)
    setPlaying(false)
  }, [total])

  const fmt = (n: number) =>
    Number.isInteger(n) || Math.abs(n - Math.round(n)) < 1e-4
      ? n.toFixed(0)
      : n.toFixed(2)

  const xScale = (i: number, n: number) =>
    PAD.l + (i / Math.max(n - 1, 1)) * (CHART_W - PAD.l - PAD.r)

  const yScale = (v: number) => {
    const { min, max } = yBounds
    return PAD.t + (1 - (v - min) / (max - min)) * (CHART_H - PAD.t - PAD.b)
  }

  const bestPath = visible
    .map((g, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i, total)} ${yScale(g.melhor.fitness)}`)
    .join(' ')

  const avgPath = visible
    .map((g, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i, total)} ${yScale(g.fitness_medio)}`)
    .join(' ')

  const maxOps = Math.max(
    1,
    ...geracoes.map((g) => g.stats?.n_cruzamentos ?? 0),
    ...geracoes.map((g) => g.stats?.n_mutacoes ?? 0),
  )

  const eventLabel = (ev: GAEvent): string => {
    switch (ev.tipo) {
      case 'selecao':
        return `Seleção: pai1=${JSON.stringify(ev.pai1)} · pai2=${JSON.stringify(ev.pai2)}`
      case 'cruzamento':
        return `Cruzamento (ponto ${String(ev.ponto)}): filhos ${JSON.stringify(ev.filho1)} / ${JSON.stringify(ev.filho2)}`
      case 'mutacao':
        return `Mutação ${String(ev.variavel)}: ${String(ev.antes)} → ${String(ev.depois)}`
      case 'sem_cruzamento':
        return 'Sem cruzamento neste par'
      default:
        return JSON.stringify(ev)
    }
  }

  if (!geracoes.length) {
    return <p className="ga-intro">Nenhuma geração registrada.</p>
  }

  return (
    <div className="ga-panel">
      <p className="ga-intro">{String(data.codificacao ?? '')}</p>
      {params && (
        <p className="ga-intro">
          População {String(params.populacao)} · Gerações {String(params.geracoes)} · Mutação{' '}
          {String(params.mutacao)} · Cruzamento {String(params.cruzamento)}
        </p>
      )}

      <div className="ga-best-card">
        <h4>Melhor indivíduo global</h4>
        <div className="ga-best-grid">
          <div className="ga-best-stat">
            Geração <strong>{melhorGeracao}</strong>
          </div>
          <div className="ga-best-stat">
            Fitness <strong>{fmt(Number(melhor?.fitness ?? 0))}</strong>
          </div>
          <div className="ga-best-stat">
            Cromossomo <strong>{JSON.stringify(melhor?.solucao ? Object.values(melhor.solucao) : [])}</strong>
          </div>
        </div>
      </div>

      <div className="ga-controls">
        <button type="button" onClick={() => setPlaying((p) => !p)} disabled={visibleCount >= total}>
          {playing ? 'Pausar' : 'Continuar'}
        </button>
        <button type="button" onClick={replay}>
          Reproduzir
        </button>
        <button type="button" onClick={showAll}>
          Ver todas
        </button>
        <label className="ga-speed">
          Velocidade
          <select
            value={speedMs}
            onChange={(e) => setSpeedMs(Number(e.target.value))}
          >
            <option value={200}>Rápida</option>
            <option value={450}>Normal</option>
            <option value={900}>Lenta</option>
          </select>
        </label>
        <span className="ga-intro">
          Geração {Math.min(visibleCount, total)}/{total} · {String(data.criterio_parada ?? '')}
        </span>
      </div>

      <div className="ga-chart-wrap">
        <svg
          className="ga-chart-svg"
          viewBox={`0 0 ${CHART_W} ${CHART_H + 56}`}
          role="img"
          aria-label="Evolução do fitness por geração"
        >
          <text x={PAD.l} y={14} fill="#94a3b8" fontSize="11">
            Fitness
          </text>
          {[0, 0.25, 0.5, 0.75, 1].map((t) => {
            const v = yBounds.min + t * (yBounds.max - yBounds.min)
            const y = yScale(v)
            return (
              <g key={t}>
                <line x1={PAD.l} y1={y} x2={CHART_W - PAD.r} y2={y} stroke="#334155" strokeWidth="1" />
                <text x={PAD.l - 6} y={y + 4} fill="#64748b" fontSize="9" textAnchor="end">
                  {fmt(v)}
                </text>
              </g>
            )
          })}

          {visible.length > 1 && (
            <>
              <path d={avgPath} fill="none" stroke="#38bdf8" strokeWidth="2" opacity="0.85" />
              <path d={bestPath} fill="none" stroke="#22c55e" strokeWidth="2.5" />
            </>
          )}

          {visible.map((g, i) => {
            const x = xScale(i, total)
            const yBest = yScale(g.melhor.fitness)
            const yAvg = yScale(g.fitness_medio)
            const isBestGen = g.geracao === melhorGeracao
            const isCurrent = i === visible.length - 1
            const barH = 40
            const barY = CHART_H + 8
            const nCr = g.stats?.n_cruzamentos ?? 0
            const nMut = g.stats?.n_mutacoes ?? 0
            return (
              <g key={g.geracao}>
                <circle cx={x} cy={yBest} r={isBestGen ? 6 : 4} fill={isBestGen ? '#22c55e' : '#4ade80'} />
                <circle cx={x} cy={yAvg} r={3} fill="#38bdf8" opacity="0.8" />
                {isCurrent && playing && (
                  <line
                    x1={x}
                    y1={PAD.t}
                    x2={x}
                    y2={CHART_H - PAD.b}
                    stroke="#fbbf24"
                    strokeWidth="1"
                    strokeDasharray="4 3"
                  />
                )}
                <rect
                  x={x - 8}
                  y={barY + barH - (nCr / maxOps) * barH}
                  width={7}
                  height={(nCr / maxOps) * barH}
                  fill="#f59e0b"
                  opacity="0.85"
                />
                <rect
                  x={x + 1}
                  y={barY + barH - (nMut / maxOps) * barH}
                  width={7}
                  height={(nMut / maxOps) * barH}
                  fill="#f472b6"
                  opacity="0.85"
                />
                <text x={x} y={CHART_H - PAD.b + 16} fill="#64748b" fontSize="9" textAnchor="middle">
                  {g.geracao}
                </text>
              </g>
            )
          })}

          <text x={PAD.l} y={CHART_H + 58} fill="#94a3b8" fontSize="10">
            Barras: cruzamentos (laranja) · mutações (rosa)
          </text>
        </svg>
        <div className="ga-legend">
          <span className="ga-legend-item">
            <span className="ga-legend-swatch" style={{ background: '#22c55e' }} />
            Melhor da geração
          </span>
          <span className="ga-legend-item">
            <span className="ga-legend-swatch" style={{ background: '#38bdf8' }} />
            Fitness médio
          </span>
          <span className="ga-legend-item">
            <span className="ga-legend-swatch" style={{ background: '#fbbf24' }} />
            Geração atual (animação)
          </span>
        </div>
      </div>

      <div className="ga-gen-list">
        {geracoes.map((g) => {
          const isBest = g.geracao === melhorGeracao
          const isCurrent = g.geracao === visible[visible.length - 1]?.geracao && playing
          const isVisible = g.geracao <= (visible[visible.length - 1]?.geracao ?? -1)
          if (!isVisible && playing) return null

          const open = expandedGen === g.geracao
          const events = g.eventos ?? []

          return (
            <div
              key={g.geracao}
              className={`ga-gen-item ${isBest ? 'ga-gen-item--best' : ''} ${isCurrent ? 'ga-gen-item--current' : ''}`}
            >
              <button
                type="button"
                className="ga-gen-summary"
                onClick={() => setExpandedGen(open ? null : g.geracao)}
              >
                <span className="ga-gen-num">Geração {g.geracao}</span>
                {isBest && <span className="ga-gen-badge ga-gen-badge--best">★ melhor global</span>}
                <span className="ga-gen-stats">
                  <span>best {fmt(g.melhor.fitness)}</span>
                  <span>média {fmt(g.fitness_medio)}</span>
                  <span>pop {g.populacao.length}</span>
                  {g.stats && (
                    <>
                      <span>✕ {g.stats.n_cruzamentos}</span>
                      <span>μ {g.stats.n_mutacoes}</span>
                    </>
                  )}
                </span>
              </button>
              {open && (
                <div className="ga-gen-body">
                  {events.length > 0 ? (
                    <div className="ga-events">
                      {events.map((ev, idx) => (
                        <div key={idx} className={`ga-event ga-event--${ev.tipo}`}>
                          {eventLabel(ev)}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="ga-events">
                      {(g.operacoes ?? []).map((op, idx) => (
                        <div key={idx} className="ga-event">
                          {op}
                        </div>
                      ))}
                    </div>
                  )}
                  <table className="ga-pop-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Cromossomo</th>
                        <th>Fitness</th>
                        <th>Viável</th>
                      </tr>
                    </thead>
                    <tbody>
                      {g.populacao.map((ind, idx) => (
                        <tr key={idx}>
                          <td>{idx + 1}</td>
                          <td>{JSON.stringify(ind.cromossomo)}</td>
                          <td>{fmt(ind.fitness)}</td>
                          <td>{ind.factivel !== false ? 'sim' : 'não'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

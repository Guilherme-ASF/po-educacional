import { Latex } from './Latex'
import './DualPanel.css'

interface DualData {
  primal?: {
    latex?: string
    solucao?: Record<string, number>
    z?: number
  }
  dual?: {
    latex?: string
    solucao?: Record<string, number>
    z?: number
    status?: string
    erro?: string
    notas_conversao?: string[]
  }
  dualidade?: {
    tipo?: string
    rotulo?: string
    descricao?: string
    z_primal?: number
    z_dual?: number
    diferenca?: number
  }
  teoria?: Record<string, string>
}

export function DualPanel({ data }: { data: DualData }) {
  const d = data.dualidade
  const tipo = d?.tipo ?? ''

  return (
    <div className="dual-panel">
      <h3>Dualidade</h3>

      <div className={`duality-badge ${tipo}`}>
        <strong>{d?.rotulo ?? 'Dualidade'}</strong>
        <p>{d?.descricao}</p>
      </div>

      <div className="dual-compare">
        <div className="dual-box primal">
          <h4>Primal — Z*</h4>
          <span className="z-val">{fmt(d?.z_primal)}</span>
          {data.primal?.solucao && (
            <ul>
              {Object.entries(data.primal.solucao).map(([k, v]) => (
                <li key={k}>
                  {k} = {Number(v).toFixed(4)}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="dual-box dual-side">
          <h4>Dual — Z*_D</h4>
          <span className="z-val">{fmt(d?.z_dual)}</span>
          {data.dual?.solucao && Object.keys(data.dual.solucao).length > 0 && (
            <ul>
              {Object.entries(data.dual.solucao).map(([k, v]) => (
                <li key={k}>
                  {k} = {Number(v).toFixed(4)}
                </li>
              ))}
            </ul>
          )}
          {data.dual?.status && data.dual.status !== 'otimo' && (
            <p className="status-warn">
              Status dual: {statusLabel(data.dual.status)}
              {data.dual.erro ? ` — ${data.dual.erro}` : ''}
            </p>
          )}
        </div>
      </div>

      <h4>Formulação primal</h4>
      <Latex tex={String(data.primal?.latex ?? '')} block />

      <h4>Formulação dual</h4>
      <Latex tex={String(data.dual?.latex ?? '')} block />

      {data.dual?.notas_conversao && data.dual.notas_conversao.length > 0 && (
        <details className="dual-notes">
          <summary>Notas de conversão primal → dual</summary>
          <ul>
            {data.dual.notas_conversao.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </details>
      )}

      {data.teoria?.folga_complementar && (
        <p className="theory">{data.teoria.folga_complementar}</p>
      )}
      {data.teoria?.interpretacao_economica && (
        <p className="theory econ">{data.teoria.interpretacao_economica}</p>
      )}
    </div>
  )
}

function statusLabel(s: string) {
  const map: Record<string, string> = {
    erro: 'erro',
    error: 'erro',
    inviavel: 'inviável',
    ilimitado: 'ilimitado',
    unbounded: 'ilimitado',
    nao_resolvido: 'não resolvido',
  }
  return map[s] ?? s
}

function fmt(v: number | undefined | null) {
  if (v === undefined || v === null) return '—'
  return Number(v).toFixed(4)
}

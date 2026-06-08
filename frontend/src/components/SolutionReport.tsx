import type { ReactNode } from 'react'
import { DualPanel } from './DualPanel'
import { Latex } from './Latex'
import { SimplexTableView } from './SimplexTable'

interface Props {
  data: Record<string, unknown>
}

export function SolutionReport({ data }: Props) {
  const id = data['1_identificacao'] as Record<string, unknown>
  const form = data['2_formulacao'] as Record<string, unknown>
  const metodo = data['3_metodo_escolhido'] as Record<string, unknown>
  const resolucao = data['4_resolucao'] as Record<string, unknown>
  const interp = data['6_interpretacao'] as Record<string, unknown>
  const conclusao = data['8_conclusao'] as Record<string, unknown>

  const diag = id?.diagnostico as Record<string, unknown>
  const metodoPrincipal = String(metodo?.metodo_principal ?? '')
  const sol = interp?.solucao as Record<string, unknown> | undefined
  const vars = sol?.variaveis as Record<string, number> | undefined
  const z = sol?.valor_objetivo as number | undefined

  return (
    <div className="report report-simple">
      <Section n={1} title="Problema">
        <div className="diag-grid">
          <Badge label="Tipo" value={String(diag?.tipo_problema ?? '')} />
          <Badge label="Objetivo" value={String(diag?.objetivo ?? '')} />
          <Badge label="Variáveis" value={String(diag?.n_variaveis ?? '')} />
        </div>
        <Latex tex={String(form?.latex ?? '')} block />
      </Section>

      <Section n={2} title={`Resolução — ${metodoPrincipal}`}>
        <p className="method-note">{String(metodo?.justificativa ?? '')}</p>
        <MethodContent resolucao={resolucao} metodo={metodoPrincipal} />
        {resolucao?.dualidade && metodoPrincipal !== 'Dualidade' && (
          <DualPanel data={resolucao.dualidade as Record<string, unknown>} />
        )}
      </Section>

      <Section n={3} title="Solução">
        {vars && (
          <div className="solution-box">
            {Object.entries(vars).map(([k, v]) => (
              <div key={k} className="sol-item">
                <span className="sol-var">{k}</span>
                <span className="sol-val">{Number(v).toFixed(4)}</span>
              </div>
            ))}
            {z !== undefined && (
              <div className="sol-z">
                Z* = <strong>{Number(z).toFixed(4)}</strong>
              </div>
            )}
          </div>
        )}
        <p className="result-line">{String(conclusao?.resultado ?? '')}</p>
      </Section>
    </div>
  )
}

function Section({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <section className="section">
      <h2>
        <span className="num">{n}</span> {title}
      </h2>
      {children}
    </section>
  )
}

function Badge({ label, value }: { label: string; value: string }) {
  return (
    <div className="badge ok">
      <span className="lbl">{label}</span>
      <span className="val">{value}</span>
    </div>
  )
}

function MethodContent({
  resolucao,
  metodo,
}: {
  resolucao: Record<string, unknown>
  metodo: string
}) {
  if (metodo === 'Simplex' && resolucao?.simplex) {
    const data = resolucao.simplex as Record<string, unknown>
    return <SimplexTableView passos={(data.passos as []) ?? []} />
  }

  if (metodo === 'Método Gráfico' && resolucao?.grafico) {
    const data = resolucao.grafico as Record<string, unknown>
    return (
      <>
        {(data.passos as Array<Record<string, unknown>>)?.map((p) => (
          <div key={String(p.passo)} className="step-card">
            <h4>Passo {String(p.passo)}</h4>
            <p>{String(p.descricao)}</p>
            <ul>
              {(p.calculos as string[])?.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </div>
        ))}
        <div
          className="svg-wrap"
          dangerouslySetInnerHTML={{ __html: String(data.svg ?? '') }}
        />
      </>
    )
  }

  if (metodo === 'Dualidade' && resolucao?.dualidade) {
    const dualData = resolucao.dualidade as Record<string, unknown>
    const simplex = resolucao.simplex as Record<string, unknown> | undefined
    const passos = (simplex?.passos as []) ?? []
    return (
      <>
        <DualPanel data={dualData} />
        {passos.length > 0 && (
          <details className="dual-simplex-detail">
            <summary>Tableau Simplex no primal</summary>
            <SimplexTableView passos={passos} />
          </details>
        )}
      </>
    )
  }

  return <p>Nenhum conteúdo de resolução para este método.</p>
}

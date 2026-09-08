import type { ReactNode } from 'react'
import { BranchBoundTree, type BBNode } from './BranchBoundTree'
import { GeneticPanel } from './GeneticPanel'
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

  const hasDuality =
    typeof resolucao?.dualidade === 'object' &&
    resolucao.dualidade !== null &&
    metodoPrincipal !== 'Dualidade'

  return (
    <div className="report report-simple">
      <Section n={1} title="Problema">
        <div className="diag-grid">
          <Badge label="Tipo" value={String(diag?.tipo_problema ?? '')} />
          <Badge label="Objetivo" value={String(diag?.objetivo ?? '')} />
          <Badge label="Variáveis" value={String(diag?.n_variaveis ?? '')} />
        </div>
        {form?.texto ? (
          <pre className="model-text">{String(form.texto)}</pre>
        ) : (
          <Latex tex={String(form?.latex ?? '')} block />
        )}
      </Section>

      <Section n={2} title={`Resolução — ${metodoPrincipal}`}>
        <p className="method-note">{String(metodo?.justificativa ?? '')}</p>
        <MethodContent resolucao={resolucao} metodo={metodoPrincipal} />
        {hasDuality && <DualPanel data={resolucao.dualidade as Record<string, unknown>} />}
      </Section>

      <Section n={3} title="Solução">
        {vars && <SolutionVars vars={vars} z={z} />}
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

function SolutionVars({ vars, z }: { vars: Record<string, number>; z?: number }) {
  const entries = Object.entries(vars)
  const active = entries.filter(([, v]) => Math.abs(Number(v)) > 1e-6)
  const compact = entries.length > 14

  if (compact) {
    return (
      <div className="solution-wrap">
        <p className="solution-summary">
          {active.length} variável(is) não nula(s) de {entries.length} no total.
        </p>
        <details className="solution-details">
          <summary>Ver todas as variáveis</summary>
          <div className="solution-box solution-box--scroll">
            {entries.map(([k, v]) => (
              <div key={k} className="sol-item">
                <span className="sol-var">{k}</span>
                <span className="sol-val">{Number(v).toFixed(4)}</span>
              </div>
            ))}
          </div>
        </details>
        {z !== undefined && (
          <div className="solution-box sol-z-row">
            <div className="sol-z">
              Z* = <strong>{Number(z).toFixed(4)}</strong>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="solution-box solution-grid">
      {entries.map(([k, v]) => (
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
  )
}

function DedicatedSolverPanel({ resolucao }: { resolucao: Record<string, unknown> }) {
  const keys = [
    'multiprocessador_exato',
    'bin_packing',
    'tsp_exato',
    'cutting_stock',
    'timetabling',
  ] as const
  const key = keys.find((k) => resolucao[k])
  if (!key) return null

  const data = resolucao[key] as Record<string, unknown>
  const nota = resolucao.nota ? String(resolucao.nota) : ''

  return (
    <div className="step-card dedicated-solver-card">
      <h4>Solver dedicado MMOL</h4>
      <p>
        <strong>Método:</strong> {String(data.metodo ?? '—')}
      </p>
      {Object.entries(data)
        .filter(([k]) => k !== 'metodo')
        .map(([k, v]) => (
          <p key={k}>
            <strong>{k}:</strong> {typeof v === 'object' ? JSON.stringify(v) : String(v)}
          </p>
        ))}
      {nota && <p className="hint">{nota}</p>}
      <p className="hint">
        Este problema usa algoritmo especializado na instância padrão; a árvore Branch &amp; Bound
        não é gerada aqui.
      </p>
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
  if (metodo === 'Algoritmo Genético' && resolucao?.algoritmo_genetico) {
    const data = resolucao.algoritmo_genetico as Record<string, unknown>
    return <GeneticPanel data={data} />
  }

  if (
    resolucao?.multiprocessador_exato ||
    resolucao?.bin_packing ||
    resolucao?.tsp_exato ||
    resolucao?.cutting_stock ||
    resolucao?.timetabling
  ) {
    return <DedicatedSolverPanel resolucao={resolucao} />
  }

  if (metodo === 'Simplex' && resolucao?.simplex) {
    const data = resolucao.simplex as Record<string, unknown>
    return <SimplexTableView passos={(data.passos as []) ?? []} />
  }

  if (metodo === 'Relaxação Linear' && resolucao?.relaxacao_linear) {
    const data = resolucao.relaxacao_linear as Record<string, unknown>
    const passos =
      (data.passos_simplex as []) ??
      (data.tabelas as unknown as []) ??
      []
    return (
      <>
        <p className="intro-text">
          Relaxação linear (variáveis contínuas) resolvida por Simplex:
        </p>
        {passos.length > 0 && <SimplexTableView passos={passos} />}
        <ul>
          {(data.analise_integralidade as string[])?.map((a, i) => (
            <li key={i}>{a}</li>
          ))}
        </ul>
      </>
    )
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

  if (metodo === 'Branch and Bound' && resolucao?.branch_and_bound) {
    const data = resolucao.branch_and_bound as Record<string, unknown>
    const nos = (data.nos as BBNode[]) ?? []
    return (
      <>
        {data.explicacao && <p className="intro-text">{String(data.explicacao)}</p>}
        {nos.length > 0 ? (
          <BranchBoundTree
            nos={nos}
            noOtimo={data.no_otimo as number | null | undefined}
          />
        ) : (
          <pre className="tree">{String(data.arvore ?? '')}</pre>
        )}
        <details className="bb-steps-detail">
          <summary>Passos detalhados do algoritmo</summary>
          {(data.passos as Array<Record<string, unknown>>)?.map((p, i) => (
            <div key={i} className="step-card">
              <h4>{String(p.titulo)}</h4>
              <p>{String(p.descricao)}</p>
            </div>
          ))}
        </details>
      </>
    )
  }

  if (
    (metodo === 'Branch and Cut' || metodo === 'Planos de Corte (Gomory)') &&
    resolucao?.branch_and_cut
  ) {
    const data = resolucao.branch_and_cut as Record<string, unknown>
    const nos = (data.nos as BBNode[]) ?? []
    return (
      <>
        {data.explicacao && <p className="intro-text">{String(data.explicacao)}</p>}
        {(data.cortes as Array<Record<string, unknown>>)?.map((c, i) => (
          <div key={i} className="step-card">
            <h4>Corte {String(c.iteracao)}</h4>
            <ul>
              {(c.calculos as string[])?.map((x, j) => (
                <li key={j}>{x}</li>
              ))}
            </ul>
          </div>
        ))}
        {nos.length > 0 ? (
          <BranchBoundTree
            nos={nos}
            noOtimo={data.no_otimo as number | null | undefined}
            nota={data.nota_arvore ? String(data.nota_arvore) : undefined}
          />
        ) : data.arvore ? (
          <pre className="tree">{String(data.arvore)}</pre>
        ) : (
          <p className="hint">Árvore de ramificação não disponível para este tamanho de modelo.</p>
        )}
        <details className="bb-steps-detail">
          <summary>Passos detalhados (B&C)</summary>
          {(data.passos as Array<Record<string, unknown>>)?.map((p, i) => (
            <div key={i} className="step-card">
              <h4>{String(p.titulo)}</h4>
              <p>{String(p.descricao)}</p>
            </div>
          ))}
        </details>
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

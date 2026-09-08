import './SimplexTable.css'
import { Latex } from './Latex'

interface PivotInfo {
  linha?: number
  coluna?: number
  coluna_nome?: string
  valor?: number
  operacao_elementar?: string[]
  matriz_identidade?: string[][]
  matriz_identidade_depois?: string[][]
  coluna_identidade?: number
  coluna_exibicao?: number
  linha_nome?: string
  operacao_elementar_latex?: string[]
}

interface LeituraTableau {
  variaveis_basicas?: Array<{ variavel: string; valor: number; coluna_B?: number; coluna_LD?: number; texto: string }>
  variaveis_nao_basicas?: Array<{ variavel: string; valor: number; texto: string }>
  z_ótimo?: number
  z_linha_Z_coluna_LD?: number
  calculo_Z?: string
  explicacao?: string[]
}

interface Step {
  iteracao?: number
  descricao?: string
  tabela?: string[][]
  tabela_antes?: string[][]
  entrante?: string
  sainte?: string
  linha_pivo?: number
  coluna_pivo_exibicao?: number
  pivot?: PivotInfo | null
  calculos?: string[]
  fase?: number
  leitura_tableau?: LeituraTableau
  matriz_identidade?: string[][]
  operacao_elementar_latex?: string[]
}

interface Props {
  passos: Step[]
}

export function SimplexTableView({ passos }: Props) {
  return (
    <div className="simplex-flow">
      {passos.map((step, si) => (
        <div key={si} className="simplex-step">
          <h4>
            {step.fase ? `Fase ${step.fase} — ` : ''}
            {step.descricao ?? `Passo ${step.iteracao ?? si}`}
          </h4>

          {(step.pivot?.matriz_identidade_depois ?? step.matriz_identidade) && (
            <div className="elementary-panel">
              <h5>Matriz elementar deste pivô ({(step.pivot?.matriz_identidade_depois ?? step.matriz_identidade)?.length ?? 0}×{(step.pivot?.matriz_identidade_depois ?? step.matriz_identidade)?.[0]?.length ?? 0})</h5>
              <IdentityMatrix
                matrix={
                  (step.pivot?.matriz_identidade_depois ??
                    step.matriz_identidade) as string[][]
                }
              />
            </div>
          )}

          {(step.pivot?.operacao_elementar_latex?.length ||
            step.operacao_elementar_latex?.length) && (
            <div className="elementary-panel">
              <h5>Operações elementares (linha a linha)</h5>
              <ol className="elem-ops latex-ops">
                {(step.pivot?.operacao_elementar_latex ?? step.operacao_elementar_latex ?? []).map(
                  (op, i) => (
                    <li key={i}>
                      <Latex tex={op} block />
                    </li>
                  )
                )}
              </ol>
            </div>
          )}

          {step.tabela_antes && step.pivot && (
            <>
              <p className="table-label">Tableau antes do pivô</p>
              <TableauGrid
                rows={step.tabela_antes}
                entering={step.entrante}
                leaving={step.sainte ?? step.pivot?.linha_nome}
                pivotCol={step.coluna_pivo_exibicao ?? step.pivot?.coluna_exibicao ?? step.pivot?.coluna}
                mode="before"
              />
            </>
          )}

          {step.leitura_tableau && (
            <TableauReadingPanel leitura={step.leitura_tableau} />
          )}

          {step.tabela && (
            <>
              <p className="table-label">
                {step.leitura_tableau
                  ? 'Tableau (referência — valores na coluna B das linhas da base)'
                  : step.tabela_antes
                    ? 'Tableau depois do pivô'
                    : 'Tableau'}
              </p>
              <TableauGrid
                rows={step.tabela}
                leitura={step.leitura_tableau}
                mode="after"
              />
            </>
          )}

          {step.calculos && step.calculos.length > 0 && (
            <ul className="calc-list">
              {step.calculos.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  )
}

function IdentityMatrix({ matrix }: { matrix: string[][] }) {
  const size = matrix.length
  if (!size) return null

  return (
    <div className="identity-wrap">
      <table className="identity-matrix">
        <tbody>
          {matrix.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j} className={cell === '1' && i === j ? 'id-one' : ''}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TableauReadingPanel({ leitura }: { leitura: LeituraTableau }) {
  return (
    <div className="reading-panel">
      <h5>Como obter x₁, x₂ e Z* deste tableau</h5>
      <div className="reading-z">
        <span className="reading-z-label">Z* (função objetivo)</span>
        <span className="reading-z-value">{Number(leitura.z_ótimo ?? 0).toFixed(4)}</span>
        <span className="reading-z-formula">{leitura.calculo_Z}</span>
      </div>
      <div className="reading-vars">
        <div className="reading-col">
          <h6>Na base (valor = coluna B)</h6>
          {(leitura.variaveis_basicas ?? []).map((b) => (
            <div key={b.variavel} className="reading-item basic">
              <code>{b.variavel}</code> = <strong>{Number(b.valor).toFixed(4)}</strong>
              <span className="hint">← B da linha {b.variavel}</span>
            </div>
          ))}
        </div>
        <div className="reading-col">
          <h6>Fora da base (= 0)</h6>
          {(leitura.variaveis_nao_basicas ?? []).map((b) => (
            <div key={b.variavel} className="reading-item">
              <code>{b.variavel}</code> = <strong>0</strong>
            </div>
          ))}
        </div>
      </div>
      <ul className="reading-explain">
        {(leitura.explicacao ?? []).map((e, i) => (
          <li key={i}>{e}</li>
        ))}
      </ul>
    </div>
  )
}

function TableauGrid({
  rows,
  entering,
  leaving,
  pivotCol,
  leitura,
  mode,
}: {
  rows: string[][]
  entering?: string
  leaving?: string
  pivotCol?: number
  leitura?: LeituraTableau
  mode: 'before' | 'after'
}) {
  if (!rows.length) return null

  const headers = rows[0]
  const dataRows = rows.slice(1)

  const colIndex = (name: string) => headers.findIndex((h) => h === name)

  const entIdx = entering ? colIndex(entering) : -1
  const pivColIdx =
    pivotCol !== undefined && pivotCol >= 0 ? pivotCol + 1 : entIdx
  const ldIdx = headers.findIndex((h) => h === 'B' || h === 'LD')
  const basicInRows = new Set(
    (leitura?.variaveis_basicas ?? []).map((b) => b.variavel)
  )

  return (
    <div className="table-scroll">
      <table className="simplex-table">
        <thead>
          <tr>
            {headers.map((h, ci) => (
              <th
                key={ci}
                className={cellClass(
                  ci,
                  entIdx,
                  pivColIdx,
                  leaving,
                  '',
                  mode,
                  true,
                  false,
                  undefined,
                  undefined,
                )}
              >
                {h}
                {mode === 'before' && ci === entIdx && ci > 0 && (
                  <span className="col-tag enter">entrante</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dataRows.map((row, ri) => {
            const rowLabel = row[0]
            const isZ = rowLabel === 'Z'
            const isBasicVar = basicInRows.has(rowLabel)
            const isLeavingRow =
              mode === 'before' && !isZ && !!leaving && rowLabel === leaving

            return (
              <tr
                key={ri}
                className={
                  isLeavingRow ? 'row-leave' : isZ ? 'row-z' : isBasicVar ? 'row-basic' : ''
                }
              >
                {row.map((cell, ci) => (
                  <td
                    key={ci}
                    className={cellClass(
                      ci,
                      entIdx,
                      pivColIdx,
                      leaving,
                      rowLabel,
                      mode,
                      false,
                      isZ,
                      ldIdx,
                      isBasicVar && ci === ldIdx,
                      isZ && ci === ldIdx
                    )}
                  >
                    {cell}
                    {isBasicVar && ci === ldIdx && (
                      <span className="col-tag value-here">= {rowLabel}</span>
                    )}
                    {isZ && ci === ldIdx && leitura && (
                      <span className="col-tag z-ld">Z no tableau</span>
                    )}
                    {mode === 'before' &&
                      isLeavingRow &&
                      ci === 0 && (
                        <span className="col-tag leave">sainte</span>
                      )}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
      {mode === 'before' && (
        <div className="legend">
          <span className="leg enter">Coluna entrante</span>
          <span className="leg leave">Linha sainte</span>
          <span className="leg pivot">Elemento pivô</span>
        </div>
      )}
      {mode === 'after' && leitura && (
        <div className="legend">
          <span className="leg ld">Coluna B = valor da variável na base</span>
        </div>
      )}
    </div>
  )
}

function cellClass(
  ci: number,
  entIdx: number,
  pivColIdx: number,
  leaving: string | undefined,
  rowLabel: string,
  mode: 'before' | 'after',
  isHeader: boolean,
  isZRow: boolean,
  ldIdx?: number,
  isLdBasic?: boolean,
  isLdZ?: boolean
): string {
  const classes: string[] = []
  if (mode === 'before' && ci === entIdx && ci > 0) classes.push('col-entering')
  if (
    mode === 'before' &&
    !isZRow &&
    !!leaving &&
    rowLabel === leaving &&
    pivColIdx >= 0 &&
    ci === pivColIdx
  ) {
    classes.push('cell-pivot')
  }
  if (mode === 'before' && isHeader && ci === pivColIdx && ci > 0) classes.push('col-entering')
  if (isLdBasic && ldIdx !== undefined && ci === ldIdx) classes.push('cell-ld-value')
  if (isLdZ && ldIdx !== undefined && ci === ldIdx) classes.push('cell-ld-z')
  return classes.join(' ')
}

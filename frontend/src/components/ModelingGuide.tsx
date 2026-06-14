import './ModelingGuide.css'

type Variant = 'standard' | 'mmol'

interface Props {
  variant?: Variant
}

const SYMBOLS = [
  { sym: '∀', label: 'para todo', example: '∀ t ∈ {1,2,3}:' },
  { sym: 'Σ', label: 'somatório', example: 'Σ_s x[t,s]' },
  { sym: '∈', label: 'pertence a', example: 't ∈ T, s ∈ S' },
  { sym: '≤ ≥ =', label: 'restrições', example: 'Σ x_i ≤ b' },
]

const NOTATION = [
  {
    token: 'p(t,s) ou p[t,s]',
    meaning: 'dado fixo (parâmetro) — ex.: tempo da tarefa t no servidor s',
  },
  {
    token: 'x[t,s] ou x_{t,s}',
    meaning: 'variável de decisão indexada — tipicamente 0 ou 1 (alocação)',
  },
  {
    token: 'x1, x2, M',
    meaning: 'variáveis escalares (formato clássico PL / PLI)',
  },
  {
    token: 'inteiro / ∈ Z',
    meaning: 'variável inteira (PLI)',
  },
  {
    token: 'binário / ∈ {0,1}',
    meaning: 'variável binária (0–1)',
  },
  {
    token: '>= 0',
    meaning: 'não negatividade (contínua ou relaxação)',
  },
]

export function ModelingGuide({ variant = 'standard' }: Props) {
  return (
    <details className="modeling-guide" open>
      <summary className="modeling-guide-toggle">
        Guia de notação para modelagem
      </summary>

      <div className="modeling-guide-body">
        <div className="modeling-symbols">
          {SYMBOLS.map((s) => (
            <div key={s.sym} className="modeling-symbol-card">
              <span className="modeling-sym">{s.sym}</span>
              <span className="modeling-sym-label">{s.label}</span>
              <code className="modeling-sym-ex">{s.example}</code>
            </div>
          ))}
        </div>

        <ul className="modeling-notation-list">
          {NOTATION.map((n) => (
            <li key={n.token}>
              <strong>{n.token}</strong> — {n.meaning}
            </li>
          ))}
        </ul>

        {variant === 'mmol' ? (
          <>
            <p className="modeling-block-title">Blocos MMOL (problemas da lista)</p>
            <ul className="modeling-notation-list modeling-blocks">
              <li>
                <strong>@dados</strong> — tabela de parâmetros (tempos, capacidade, etc.)
              </li>
              <li>
                <strong>@modelo</strong> — função objetivo e restrições com ∀ e Σ
              </li>
              <li>
                <strong>@dominio</strong> — conjuntos T, S, … (opcional)
              </li>
            </ul>
            <pre className="modeling-example">{MMOL_EXAMPLE}</pre>
          </>
        ) : (
          <>
            <p className="modeling-block-title">Exemplos rápidos</p>
            <pre className="modeling-example">{STANDARD_PLI}</pre>
            <pre className="modeling-example">{STANDARD_INDEXED}</pre>
          </>
        )}

        <p className="modeling-footnote">
          Linhas com <code>#</code> são comentários. O parser expande ∀ e Σ automaticamente
          quando possível.
        </p>
      </div>
    </details>
  )
}

const STANDARD_PLI = `Max Z = 2x1 + 3x2
S.A.
x1 + x2 <= 6
x1, x2 >= 0
x1, x2 inteiro`

const STANDARD_INDEXED = `Min Z = M
S.A.
∀ t: Σ_s x[t,s] = 1
∀ s: Σ_t p[t,s] * x[t,s] <= M
x[t,s] binário`

const MMOL_EXAMPLE = `@dados
tempos:
  - [4, 5, 3, 7]
  - [3, 6, 4, 5]
capacidade: 12

@modelo
Min Z = M
∀ t: Σ_s x[t,s] = 1
∀ s: Σ_t p[t,s]·x[t,s] ≤ M
x[t,s] binário`

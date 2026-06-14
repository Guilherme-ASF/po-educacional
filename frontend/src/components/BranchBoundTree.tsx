import { useEffect, useMemo, useRef, useState, type PointerEvent, type ReactNode } from 'react'
import './BranchBoundTree.css'
import { SimplexTableView } from './SimplexTable'

export interface BBNode {
  id: number
  rotulo: string
  pai: number | null
  tipo_exibicao: string
  poda?: string | null
  z_relax?: number | null
  z_inteiro?: number | null
  solucao?: Record<string, number>
  passos_simplex?: unknown[]
  ramificacao?: {
    rotulo?: string | null
  }
}

interface Props {
  nos: BBNode[]
  noOtimo?: number | null
  nota?: string
}

const TIPO_LABEL: Record<string, string> = {
  viavel: 'Viável (inteiro)',
  relaxacao: 'Relaxação LP',
  incumbente: 'Incumbente',
  inviavel: 'Inviável',
  otimo: '★ Ótimo',
  podado: 'Podado',
  pendente: 'Pendente',
}

const MIN_ZOOM = 0.25
const MAX_ZOOM = 2.5

export function BranchBoundTree({ nos, noOtimo, nota }: Props) {
  const [selected, setSelected] = useState<BBNode | null>(null)

  const childrenMap = useMemo(() => {
    const map = new Map<number | null, BBNode[]>()
    for (const n of nos) {
      const p = n.pai ?? null
      if (!map.has(p)) map.set(p, [])
      map.get(p)!.push(n)
    }
    for (const kids of map.values()) {
      kids.sort((a, b) => a.id - b.id)
    }
    return map
  }, [nos])

  const roots = childrenMap.get(null) ?? []

  if (!roots.length) {
    return <p className="bb-empty">Nenhum nó na árvore.</p>
  }

  return (
    <div className="bb-tree-wrap">
      {nota && <p className="bb-hint">{nota}</p>}
      <p className="bb-hint">
        Clique em um nó para o tableau. Arraste o fundo para mover; roda do mouse ou botões para zoom.
        Nós com valores fracionários são <strong>relaxação LP</strong> — só soluções inteiras são viáveis no PLI.
      </p>
      <PanViewport resetKey={nos.length}>
        {roots.map((root) => (
          <TreeBranch
            key={root.id}
            node={root}
            childrenMap={childrenMap}
            onSelect={setSelected}
            noOtimo={noOtimo}
          />
        ))}
      </PanViewport>
      {selected && <NodeModal node={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}

function PanViewport({ children, resetKey }: { children: ReactNode; resetKey: number }) {
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [scale, setScale] = useState(1)
  const dragging = useRef(false)
  const start = useRef({ mx: 0, my: 0, ox: 0, oy: 0 })
  const viewportRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setOffset({ x: 0, y: 0 })
    setScale(1)
  }, [resetKey])

  useEffect(() => {
    const el = viewportRef.current
    if (!el) return
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      const rect = el.getBoundingClientRect()
      const mx = e.clientX - rect.left
      const my = e.clientY - rect.top
      const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1
      setScale((prev) => {
        const next = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, prev * factor))
        const ratio = next / prev
        setOffset((o) => ({
          x: mx - ratio * (mx - o.x),
          y: my - ratio * (my - o.y),
        }))
        return next
      })
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [])

  const zoomByFactor = (factor: number) => {
    const el = viewportRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const cx = rect.width / 2
    const cy = rect.height / 2
    setScale((prev) => {
      const next = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, prev * factor))
      const ratio = next / prev
      setOffset((o) => ({
        x: cx - ratio * (cx - o.x),
        y: cy - ratio * (cy - o.y),
      }))
      return next
    })
  }

  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest('button')) return
    dragging.current = true
    start.current = { mx: e.clientX, my: e.clientY, ox: offset.x, oy: offset.y }
    e.currentTarget.setPointerCapture(e.pointerId)
  }

  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    if (!dragging.current) return
    setOffset({
      x: start.current.ox + e.clientX - start.current.mx,
      y: start.current.oy + e.clientY - start.current.my,
    })
  }

  const endDrag = (e: PointerEvent<HTMLDivElement>) => {
    if (!dragging.current) return
    dragging.current = false
    try {
      e.currentTarget.releasePointerCapture(e.pointerId)
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="bb-pan-shell">
      <div className="bb-zoom-toolbar">
        <button type="button" className="bb-zoom-btn" onClick={() => zoomByFactor(1.2)} title="Zoom +">
          +
        </button>
        <button type="button" className="bb-zoom-btn" onClick={() => zoomByFactor(1 / 1.2)} title="Zoom −">
          −
        </button>
        <button
          type="button"
          className="bb-zoom-btn bb-zoom-btn--reset"
          onClick={() => {
            setOffset({ x: 0, y: 0 })
            setScale(1)
          }}
          title="Resetar"
        >
          ⟲
        </button>
        <span className="bb-zoom-label">{Math.round(scale * 100)}%</span>
      </div>
      <div
        ref={viewportRef}
        className="bb-pan-viewport"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
      >
        <div
          className="bb-pan-layer"
          style={{
            transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`,
            transformOrigin: '0 0',
          }}
        >
          <div className="bb-tree-inner">{children}</div>
        </div>
      </div>
    </div>
  )
}

function TreeBranch({
  node,
  childrenMap,
  onSelect,
  noOtimo,
}: {
  node: BBNode
  childrenMap: Map<number | null, BBNode[]>
  onSelect: (n: BBNode) => void
  noOtimo?: number | null
}) {
  const children = childrenMap.get(node.id) ?? []
  const infeasibleChild = (c: BBNode) => c.tipo_exibicao === 'inviavel'

  return (
    <div className="bb-subtree">
      <div className="bb-node-slot">
        <NodeCard node={node} onClick={() => onSelect(node)} highlight={noOtimo === node.id} />
      </div>
      {children.length > 0 && (
        <div className="bb-children-block">
          <div className="bb-connector-down" />
          <div className={`bb-children-row bb-children-row--${children.length}`}>
            {children.map((child) => (
              <div key={child.id} className="bb-child-col">
                <div
                  className={`bb-connector-up ${infeasibleChild(child) ? 'bb-connector-up--dashed' : ''}`}
                />
                {child.ramificacao?.rotulo && (
                  <span className="bb-edge-label">{child.ramificacao.rotulo}</span>
                )}
                <TreeBranch
                  node={child}
                  childrenMap={childrenMap}
                  onSelect={onSelect}
                  noOtimo={noOtimo}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function NodeCard({
  node,
  onClick,
  highlight,
}: {
  node: BBNode
  onClick: () => void
  highlight?: boolean
}) {
  const tipo = node.tipo_exibicao || 'pendente'
  const z = node.z_inteiro ?? node.z_relax
  const zRelax = node.z_inteiro != null ? node.z_relax : null
  const showDualZ =
    zRelax != null &&
    node.z_inteiro != null &&
    Math.abs(Number(zRelax) - Number(node.z_inteiro)) > 1e-3
  const isInfeasible = tipo === 'inviavel'
  const isPodado = tipo === 'podado'
  const isRelaxacao = tipo === 'relaxacao'

  return (
    <button
      type="button"
      className={`bb-node bb-node--${tipo} ${highlight ? 'bb-node--highlight' : ''}`}
      onClick={onClick}
      title="Clique para ver o tableau"
    >
      <div className="bb-node-head">
        <span className="bb-node-id">{node.rotulo}</span>
        <span className={`bb-node-badge bb-node-badge--${tipo}`}>
          {TIPO_LABEL[tipo] ?? tipo}
        </span>
      </div>
      {isInfeasible ? (
        <div className="bb-node-z bb-node-z--fail">LP Inviável</div>
      ) : z !== undefined && z !== null ? (
        <div className="bb-node-z">
          {tipo === 'otimo' ? (
            <>
              Z<sup>*</sup> = <strong>{fmt(z)}</strong>
            </>
          ) : (
            <>
              Z = <strong>{fmt(z)}</strong>
            </>
          )}
          {showDualZ && (
            <span className="bb-node-z-relax"> (relax. {fmt(Number(zRelax))})</span>
          )}
        </div>
      ) : (
        <div className="bb-node-z bb-node-z--muted">—</div>
      )}
      <div className="bb-node-foot">
        {isInfeasible ? (
          <span className="bb-node-meta">sem solução factível</span>
        ) : isRelaxacao ? (
          <span className="bb-node-meta">limitante — valores não inteiros</span>
        ) : node.solucao && Object.keys(node.solucao).length > 0 ? (
          <span className="bb-node-sol">{formatSol(node.solucao)}</span>
        ) : isPodado && node.poda ? (
          <span className="bb-node-meta">{shortPrune(node.poda)}</span>
        ) : null}
      </div>
    </button>
  )
}

function NodeModal({ node, onClose }: { node: BBNode; onClose: () => void }) {
  const passos = (node.passos_simplex as []) ?? []
  const z = node.z_inteiro ?? node.z_relax
  const zRelax = node.z_relax
  const showDualZ =
    node.z_inteiro != null &&
    zRelax != null &&
    Math.abs(Number(zRelax) - Number(node.z_inteiro)) > 1e-3

  return (
    <div className="bb-modal-overlay" onClick={onClose} role="presentation">
      <div
        className="bb-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="bb-modal-title"
      >
        <header className="bb-modal-header">
          <div>
            <h3 id="bb-modal-title">{node.rotulo}</h3>
            <p className="bb-modal-sub">
              {TIPO_LABEL[node.tipo_exibicao] ?? node.tipo_exibicao}
              {z !== undefined && z !== null && (
                <>
                  {' · '}
                  {node.tipo_exibicao === 'otimo' ? `Z* = ${fmt(z)}` : `Z = ${fmt(z)}`}
                </>
              )}
              {showDualZ && zRelax != null && (
                <> · relaxação LP = {fmt(Number(zRelax))}</>
              )}
            </p>
          </div>
          <button type="button" className="bb-modal-close" onClick={onClose} aria-label="Fechar">
            ×
          </button>
        </header>
        <div className="bb-modal-body">
          {node.tipo_exibicao === 'inviavel' ? (
            <p className="bb-modal-infeas">Este subproblema não possui solução factível.</p>
          ) : passos.length > 0 ? (
            <SimplexTableView passos={passos} />
          ) : node.solucao && Object.keys(node.solucao).length > 0 ? (
            <div className="bb-modal-fallback">
              <p className="bb-modal-infeas">Tableau não disponível; solução da relaxação neste nó:</p>
              <ul className="bb-modal-sol-list">
                {Object.entries(node.solucao)
                  .filter(([, v]) => Math.abs(Number(v)) > 1e-6)
                  .map(([k, v]) => (
                    <li key={k}>
                      <code>{k}</code> = {fmt(Number(v))}
                    </li>
                  ))}
              </ul>
              {z !== undefined && z !== null && (
                <p className="bb-modal-z">
                  Z = <strong>{fmt(z)}</strong>
                </p>
              )}
            </div>
          ) : (
            <p className="bb-modal-infeas">Tableau não disponível para este nó.</p>
          )}
        </div>
      </div>
    </div>
  )
}

function fmt(n: number) {
  return Number.isInteger(n) || Math.abs(n - Math.round(n)) < 1e-4
    ? Number(n).toFixed(2)
    : Number(n).toFixed(4)
}

function formatSol(sol: Record<string, number>) {
  const active = Object.entries(sol).filter(([, v]) => Math.abs(v) > 1e-6)
  if (active.length === 0) return '(0)'
  if (active.length > 4) {
    return active
      .slice(0, 2)
      .map(([k, v]) => `${k}=${fmt(v)}`)
      .join(', ')
      .concat(`… (+${active.length - 2})`)
  }
  return `(${active.map(([, v]) => fmt(v)).join('; ')})`
}

function shortPrune(reason: string) {
  if (reason.toLowerCase().includes('dominância')) return 'limite superior'
  if (reason.toLowerCase().includes('inviabilidade')) return 'LP inviável'
  return reason
}

import katex from 'katex'

export function Latex({ tex, block = false }: { tex: string; block?: boolean }) {
  try {
    const html = katex.renderToString(tex, {
      throwOnError: false,
      displayMode: block,
    })
    return block ? (
      <div className="latex-block" dangerouslySetInnerHTML={{ __html: html }} />
    ) : (
      <span className="latex-inline" dangerouslySetInnerHTML={{ __html: html }} />
    )
  } catch {
    return <code>{tex}</code>
  }
}

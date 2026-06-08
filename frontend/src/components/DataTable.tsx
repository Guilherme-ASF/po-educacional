interface Props {
  headers?: string[]
  rows: (string | number)[][]
  title?: string
}

export function DataTable({ headers, rows, title }: Props) {
  const cols = headers ?? (rows[0]?.map((_, i) => `Col ${i + 1}`) ?? [])
  const body = headers ? rows : rows

  return (
    <div className="table-wrap">
      {title && <h4>{title}</h4>}
      <table>
        <thead>
          <tr>
            {cols.map((h, i) => (
              <th key={i}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, ri) => (
            <tr key={ri}>
              {row.map((cell, ci) => (
                <td key={ci}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

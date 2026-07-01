import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { ErrorBox, Loader } from '../components.jsx'
import { useAsync } from '../useAsync.js'

export default function CoreViewer() {
  const tables = useAsync(api.coreTables, [])
  const [selected, setSelected] = useState(null)

  // По умолчанию открываем deals, как только список таблиц пришёл.
  useEffect(() => {
    if (!selected && tables.data && tables.data.length) {
      const preferred = tables.data.find((t) => t.name === 'deals') || tables.data[0]
      setSelected(preferred.name)
    }
  }, [tables.data, selected])

  if (tables.loading) return <Loader />
  if (tables.error) return <ErrorBox error={tables.error} />

  return (
    <section className="core-layout">
      <aside className="sidebar">
        <div className="sidebar-title">Core-таблицы</div>
        <ul className="table-list">
          {tables.data.map((t) => (
            <li key={t.name}>
              <button
                className={`table-item ${selected === t.name ? 'active' : ''}`}
                onClick={() => setSelected(t.name)}
              >
                <span>{t.label}</span>
                <span className="pill">{t.count}</span>
              </button>
            </li>
          ))}
        </ul>
      </aside>
      <div className="core-main">{selected ? <TableView name={selected} /> : <Loader />}</div>
    </section>
  )
}

function TableView({ name }) {
  const state = useAsync(() => api.coreTable(name), [name])
  if (state.loading) return <Loader />
  if (state.error) return <ErrorBox error={state.error} />

  const { label, columns, rows } = state.data
  return (
    <section>
      <h1 className="page-title">
        {label} <span className="muted mono">({name})</span>
      </h1>
      <p className="muted page-lead">
        Строк: {rows.length}. Строки с бизнес-сигналом подсвечены (флаг качества).
      </p>
      <div className="table-wrap">
        <table className="grid">
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className={r.has_quality_issue ? 'row-flagged' : ''}>
                {columns.map((c) => (
                  <td key={c} className="mono">
                    {fmt(r[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function fmt(v) {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'boolean') return v ? 'да' : 'нет'
  return String(v)
}

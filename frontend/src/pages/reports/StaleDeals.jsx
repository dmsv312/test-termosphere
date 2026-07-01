import { useState } from 'react'
import { api } from '../../api.js'
import { useAsync } from '../../useAsync.js'
import { ReportView } from './shared.jsx'

export default function StaleDeals() {
  const [n, setN] = useState(14)
  const state = useAsync(() => api.reportStale(n), [n])
  return (
    <ReportView
      title="Сделки без активности N дней"
      lead="Живые сделки (не выигранные и не проигранные), по которым от даты среза до последнего касания прошло больше N дней, либо активностей не было вовсе. Касание — только записи активностей (звонок/письмо/задача)."
      state={state}
    >
      {(data) => (
        <div className="panel">
          <div className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <span>
              Без активности ({data.rows.length}){' '}
              <span className="muted">· дата среза {data.cutoff_date}</span>
            </span>
            <label className="muted" style={{ marginLeft: 'auto', fontWeight: 400 }}>
              N, дней:{' '}
              <input
                type="number"
                min={0}
                max={3650}
                value={n}
                onChange={(e) => setN(Math.min(3650, Math.max(0, Number(e.target.value) || 0)))}
                style={{ width: 72, padding: '4px 8px' }}
              />
            </label>
          </div>
          {data.rows.length === 0 ? (
            <p className="muted">Все живые сделки касались за последние {data.n_days} дней.</p>
          ) : (
            <div className="table-wrap">
              <table className="grid">
                <thead>
                  <tr>
                    <th>Сделка</th>
                    <th>Стадия</th>
                    <th>Последнее касание</th>
                    <th>Дней без активности</th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((r) => (
                    <tr key={r.deal_id} className="row-flagged">
                      <td className="mono">{r.deal_id}</td>
                      <td className="mono">{r.stage_id ?? '—'}</td>
                      <td className="mono">
                        {r.last_touch ?? <span className="muted">нет активностей</span>}
                      </td>
                      <td>{r.days_since ?? <span className="muted">— (никогда)</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </ReportView>
  )
}

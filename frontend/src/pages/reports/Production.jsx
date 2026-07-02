import { api } from '../../api.js'
import { useAsync } from '../../useAsync.js'
import { ReportView } from './shared.jsx'

export default function Production() {
  const state = useAsync(api.reportProduction, [])
  return (
    <ReportView
      title="Задержка производства > 5 дней"
      lead="Производственные заказы, которые опаздывают: фактическое завершение (а для незавершённых — дата среза) позже планового больше чем на 5 дней."
      state={state}
    >
      {(data) => (
        <div className="panel">
          <div className="panel-title">
            Задержанные заказы ({data.rows.length}){' '}
            <span className="muted">· дата среза {data.cutoff_date}, порог {data.threshold_days} дн.</span>
          </div>
          {data.rows.length === 0 ? (
            <p className="muted">Заказов с задержкой более {data.threshold_days} дней нет.</p>
          ) : (
            <div className="table-wrap">
              <table className="grid">
                <thead>
                  <tr>
                    <th>Заказ</th>
                    <th>Сделка</th>
                    <th>Статус</th>
                    <th>Плановое завершение</th>
                    <th>Фактическое завершение</th>
                    <th>Задержка, дн.</th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((r) => (
                    <tr key={r.production_order_id} className="row-flagged">
                      <td className="mono">{r.production_order_id}</td>
                      <td className="mono">{r.deal_id}</td>
                      <td>{r.status ?? '—'}</td>
                      <td className="mono">{r.planned_finish_at ?? '—'}</td>
                      <td className="mono">
                        {r.actual_finish_at ?? (
                          <span className="muted">в работе (по срезу {data.cutoff_date})</span>
                        )}
                      </td>
                      <td>
                        <strong>{r.delay_days}</strong>
                      </td>
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

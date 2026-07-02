import { api } from '../../api.js'
import { useAsync } from '../../useAsync.js'
import { Money, money, ReportView } from './shared.jsx'

export default function Managers() {
  const state = useAsync(api.reportManagers, [])
  return (
    <ReportView
      title="Продажи и маржа по менеджерам"
      lead="Выручка и маржа по каждому менеджеру — по выигранным сделкам. Менеджеры без продаж тоже показаны. Если у выигранной сделки нет позиций, маржу по ней посчитать нельзя — в итог она не входит."
      state={state}
    >
      {(data) => (
        <>
          <div className="panel">
            <div className="panel-title">Менеджеры (по выигранным сделкам)</div>
            <div className="table-wrap">
              <table className="grid">
                <thead>
                  <tr>
                    <th>Менеджер</th>
                    <th>Статус</th>
                    <th>Выиграно</th>
                    <th>Выручка</th>
                    <th>Маржа</th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((r) => (
                    <tr key={r.user_id} className={r.active ? '' : 'row-flagged'}>
                      <td>
                        {r.name} <span className="muted mono">({r.user_id})</span>
                      </td>
                      <td>{r.active ? 'активен' : 'неактивен'}</td>
                      <td>{r.won_deals}</td>
                      <td>{money(r.revenue)}</td>
                      <td>
                        {money(r.margin)}
                        {r.won_without_margin > 0 && (
                          <span className="muted"> · без позиций: {r.won_without_margin}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted" style={{ marginTop: 10 }}>
              Строка подсвечена, если сделка закреплена за неактивным сотрудником, — такие сделки стоит переназначить.
            </p>
          </div>

          {data.shipped_not_closed.length > 0 && (
            <div className="panel">
              <div className="panel-title">Отгружено, но не закрыто</div>
              <p className="muted page-lead">
                Товар отгружен и оплачен, но сделку ещё не перевели в «Успешно». Выносим отдельно,
                чтобы такие продажи не потерялись и не смешивались с закрытыми.
              </p>
              <div className="table-wrap">
                <table className="grid">
                  <thead>
                    <tr>
                      <th>Сделка</th>
                      <th>Менеджер</th>
                      <th>Сумма</th>
                      <th>Маржа</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.shipped_not_closed.map((r) => (
                      <tr key={r.deal_id}>
                        <td className="mono">{r.deal_id}</td>
                        <td>{r.manager_name ?? '—'}</td>
                        <td>{money(r.amount)}</td>
                        <td>
                          <Money value={r.margin} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </ReportView>
  )
}

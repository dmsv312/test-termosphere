import { api } from '../../api.js'
import { useAsync } from '../../useAsync.js'
import { Money, money, ReportView } from './shared.jsx'

export default function Managers() {
  const state = useAsync(api.reportManagers, [])
  return (
    <ReportView
      title="Продажи и маржа по менеджерам"
      lead="По выигранным сделкам (стадия «Успешно»): выручка = сумма сделок, маржа = сумма маржи по позициям. Менеджеры без продаж тоже в списке. Где у выигранной сделки нет позиций, маржа неизвестна и в сумму не входит."
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
                    <th>Выигранных</th>
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
              Неактивный менеджер, владеющий сделкой, — управленческий сигнал (строка подсвечена).
            </p>
          </div>

          {data.shipped_not_closed.length > 0 && (
            <div className="panel">
              <div className="panel-title">Отгружено, но не закрыто</div>
              <p className="muted page-lead">
                Фактическая продажа (товар отгружен и оплачен), но сделка ещё не переведена в
                «Успешно». Показываем отдельно, чтобы не терять продажу и не смешивать с закрытыми.
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

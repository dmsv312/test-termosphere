import { api } from '../../api.js'
import { useAsync } from '../../useAsync.js'
import { Money, money, ReportView } from './shared.jsx'

export default function Receivables() {
  const state = useAsync(api.reportReceivables, [])
  return (
    <ReportView
      title="Дебиторка"
      lead="Сколько клиенты ещё должны. Берём сделки на стадии «Договор» и дальше, а также все, по которым были оплаты (кроме проигранных). Остаток = сумма − оплачено + корректировки. Оплаты «в ожидании» долг не уменьшают и вынесены в отдельную колонку; отрицательный остаток означает переплату."
      state={state}
    >
      {(data) => (
        <div className="panel">
          <div className="panel-title">Остатки по сделкам</div>
          <div className="table-wrap">
            <table className="grid">
              <thead>
                <tr>
                  <th>Сделка</th>
                  <th>Стадия</th>
                  <th>Сумма</th>
                  <th>Оплачено</th>
                  <th>В ожидании</th>
                  <th>Корректировка</th>
                  <th>Остаток</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r) => (
                  <tr key={r.deal_id} className={Number(r.balance) < 0 ? 'row-flagged' : ''}>
                    <td className="mono">{r.deal_id}</td>
                    <td className="mono">{r.stage_id ?? '—'}</td>
                    <td>{money(r.amount)}</td>
                    <td>{money(r.paid)}</td>
                    <td>{Number(r.pending) ? money(r.pending) : '—'}</td>
                    <td>{Number(r.correction) ? money(r.correction) : '—'}</td>
                    <td>
                      <strong>
                        <Money value={r.balance} />
                      </strong>
                      {Number(r.balance) < 0 && <span className="muted"> · переплата</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="row-total">
                  <td colSpan={2}>Итого</td>
                  <td>{money(data.totals.amount)}</td>
                  <td>{money(data.totals.paid)}</td>
                  <td>{money(data.totals.pending)}</td>
                  <td>{money(data.totals.correction)}</td>
                  <td>{money(data.totals.balance)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}
    </ReportView>
  )
}

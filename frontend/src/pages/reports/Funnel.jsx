import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../../api.js'
import { useAsync } from '../../useAsync.js'
import { money, ReportView } from './shared.jsx'

// Цвет столбца: выигранные — зелёный, проигранные — красный, «в работе» — синий.
function barColor(row) {
  if (row.is_success) return '#2da44e'
  if (row.stage_id === 'LOST') return '#cf222e'
  return '#0969da'
}

export default function Funnel() {
  const state = useAsync(api.reportFunnel, [])
  return (
    <ReportView
      title="Воронка продаж"
      lead="Количество сделок и их сумма по стадиям. Сумма — гибрид: по позициям сделки, а где позиций нет — оценка из карточки. Видно, на каких стадиях «висят» деньги."
      state={state}
    >
      {(data) => {
        const chart = data.rows.map((r) => ({ ...r, amountNum: Number(r.amount) }))
        return (
          <>
            <div className="panel">
              <div className="panel-title">Сумма сделок по стадиям</div>
              <ResponsiveContainer width="100%" height={340}>
                <BarChart data={chart} margin={{ top: 8, right: 16, left: 8, bottom: 72 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="stage_name"
                    angle={-30}
                    textAnchor="end"
                    interval={0}
                    height={72}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis
                    // низ шкалы — 0 (или чуть ниже, если есть отрицательная сумма из грязных данных),
                    // а не «красивое» -125к: не раздуваем пустую зону под нулём
                    domain={([min, max]) => [Math.min(0, min) * 1.1, max * 1.05]}
                    tickFormatter={(v) => (v / 1000).toLocaleString('ru-RU') + 'к'}
                  />
                  <Tooltip formatter={(v) => money(v)} />
                  {/* нулевая линия = визуальная базовая ось, от неё растут столбцы */}
                  <ReferenceLine y={0} stroke="#8a8f98" />
                  <Bar dataKey="amountNum" name="Сумма" isAnimationActive={false}>
                    {chart.map((r) => (
                      <Cell key={r.sort_order} fill={barColor(r)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="panel">
              <div className="panel-title">По стадиям</div>
              <div className="table-wrap">
                <table className="grid">
                  <thead>
                    <tr>
                      <th>Стадия</th>
                      <th>Код</th>
                      <th>Сделок</th>
                      <th>Сумма</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.rows.map((r) => (
                      <tr key={r.sort_order} className={r.is_success ? 'row-won' : ''}>
                        <td>{r.stage_name}</td>
                        <td className="mono">{r.stage_id ?? '—'}</td>
                        <td>{r.deals}</td>
                        <td>{money(r.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="row-total">
                      <td colSpan={2}>Итого</td>
                      <td>{data.totals.deals}</td>
                      <td>{money(data.totals.amount)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          </>
        )
      }}
    </ReportView>
  )
}

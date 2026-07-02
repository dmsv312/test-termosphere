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

// Округляем ось Y до ровных значений (иначе авто-домен даёт «379,05к» и т.п.).
// Шаг подбираем под размах; нижняя граница = 0 либо ровный отрицательный (грязь).
function yAxis(values) {
  const max = Math.max(0, ...values)
  const min = Math.min(0, ...values)
  const step = max - min > 400000 ? 100000 : 50000
  const lo = Math.floor(min / step) * step
  const hi = Math.ceil(max / step) * step
  const ticks = []
  for (let t = lo; t <= hi + 1; t += step) ticks.push(t)
  return { domain: [lo, hi], ticks }
}

const yTick = (v) => (v === 0 ? '0' : (v / 1000).toLocaleString('ru-RU') + 'к')

export default function Funnel() {
  const state = useAsync(api.reportFunnel, [])
  return (
    <ReportView
      title="Воронка продаж"
      lead="Сколько сделок и на какую сумму находится на каждой стадии воронки. Сумму берём по позициям сделки, а если позиций нет — оценку из карточки. Сразу видно, где скапливаются деньги."
      state={state}
    >
      {(data) => {
        const chart = data.rows.map((r) => ({ ...r, amountNum: Number(r.amount) }))
        const y = yAxis(chart.map((r) => r.amountNum))
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
                  <YAxis domain={y.domain} ticks={y.ticks} tickFormatter={yTick} />
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
              <div className="chart-legend">
                <span><i style={{ background: '#2da44e' }} /> Выиграно</span>
                <span><i style={{ background: '#0969da' }} /> В работе</span>
                <span><i style={{ background: '#cf222e' }} /> Проиграно</span>
              </div>
            </div>

            <div className="panel">
              <div className="panel-title">Детально по стадиям</div>
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

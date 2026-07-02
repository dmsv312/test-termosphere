import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../../api.js'
import { useAsync } from '../../useAsync.js'
import { Money, money, ReportView, romi } from './shared.jsx'

export default function Sources() {
  const state = useAsync(api.reportSources, [])
  return (
    <ReportView
      title="Источники заявок: выручка, маржа и окупаемость"
      lead="Отдача каналов привлечения: сколько сделок пришло и сколько выиграно, выручка и маржа по выигранным, расходы на рекламу. ROMI = (выручка − затраты) / затраты; по каналам без расходов показатель не считаем."
      state={state}
    >
      {(data) => {
        const chart = data.rows.map((r) => ({
          name: r.name,
          revenue: Number(r.revenue),
          costs: Number(r.costs),
        }))
        return (
          <>
            <div className="panel">
              <div className="panel-title">Выручка и затраты по каналам</div>
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={chart} margin={{ top: 8, right: 16, left: 8, bottom: 56 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" interval={0} height={56} tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={(v) => (v === 0 ? '0' : (v / 1000).toLocaleString('ru-RU') + 'к')} />
                  <Tooltip formatter={(v) => money(v)} />
                  <Legend verticalAlign="top" height={28} />
                  <Bar dataKey="revenue" name="Выручка (выигранные)" fill="#2da44e" isAnimationActive={false} />
                  <Bar dataKey="costs" name="Затраты на рекламу" fill="#cf222e" isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="panel">
              <div className="panel-title">По каналам</div>
              <div className="table-wrap">
                <table className="grid">
                  <thead>
                    <tr>
                      <th>Канал</th>
                      <th>Сделок</th>
                      <th>Выиграно</th>
                      <th>Выручка</th>
                      <th>Маржа</th>
                      <th>Затраты</th>
                      <th>ROMI</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.rows.map((r) => (
                      <tr key={r.id}>
                        <td>
                          {r.name} <span className="muted mono">({r.code})</span>
                        </td>
                        <td>{r.deals}</td>
                        <td>{r.won_deals}</td>
                        <td>{money(r.revenue)}</td>
                        <td>
                          <Money value={r.margin} />
                        </td>
                        <td>{money(r.costs)}</td>
                        <td className={r.romi !== null && r.romi < 0 ? 'neg' : ''}>
                          {r.has_costs ? romi(r.romi) : <span className="muted">нет затрат</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )
      }}
    </ReportView>
  )
}

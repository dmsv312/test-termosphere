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
import { api } from '../api.js'
import { ActionBadge, ErrorBox, Loader } from '../components.jsx'
import { useAsync } from '../useAsync.js'

// Серии графика = три реакции (цвета согласованы с бейджами в таблице).
const ACTION_SERIES = [
  { key: 'fixed', name: 'Исправлено', fill: '#2da44e' },
  { key: 'quarantined', name: 'Карантин', fill: '#cf222e' },
  { key: 'flagged', name: 'Флаг', fill: '#d4a72c' },
]

const rowTotal = (r) => r.fixed + r.quarantined + r.flagged

// by_type: [{issue_type, action, count}] → строки {issue_type, fixed, quarantined, flagged}.
function pivotByType(byType) {
  const map = new Map()
  for (const { issue_type, action, count } of byType) {
    const row = map.get(issue_type) || { issue_type, fixed: 0, quarantined: 0, flagged: 0 }
    row[action] = (row[action] || 0) + count
    map.set(issue_type, row)
  }
  return [...map.values()].sort((a, b) => rowTotal(b) - rowTotal(a))
}

export default function DataQuality() {
  const summary = useAsync(api.dqSummary, [])
  const issues = useAsync(api.dqIssues, [])

  if (summary.error) return <ErrorBox error={summary.error} />
  if (issues.error) return <ErrorBox error={issues.error} />
  if (summary.loading || issues.loading) return <Loader />

  const { total, by_action } = summary.data
  const pivot = pivotByType(summary.data.by_type)

  return (
    <section>
      <h1 className="page-title">
        Проблемы данных <span className="muted">— отчёт №7</span>
      </h1>
      <p className="muted page-lead">
        Что пайплайн raw→core нашёл в выгрузке и как отреагировал. Три реакции: исправлено
        (нормализовали), карантин (не пустили в отчёты, но сохранили в логе), флаг (бизнес-сигнал —
        оставили и пометили).
      </p>

      <div className="cards">
        <Card label="Всего проблем" value={total} tone="total" />
        <Card label="Исправлено" value={by_action.fixed} tone="fixed" />
        <Card label="Карантин" value={by_action.quarantined} tone="quarantined" />
        <Card label="Флаг" value={by_action.flagged} tone="flagged" />
      </div>

      <div className="panel">
        <div className="panel-title">По типам проблем × реакция</div>
        <ResponsiveContainer width="100%" height={380}>
          <BarChart data={pivot} margin={{ top: 8, right: 16, left: 0, bottom: 96 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="issue_type"
              angle={-35}
              textAnchor="end"
              interval={0}
              height={96}
              tick={{ fontSize: 11 }}
            />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Legend />
            {ACTION_SERIES.map((s) => (
              <Bar key={s.key} dataKey={s.key} stackId="a" name={s.name} fill={s.fill} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="panel">
        <div className="panel-title">Все проблемы ({issues.data.length})</div>
        <div className="table-wrap">
          <table className="grid">
            <thead>
              <tr>
                <th>Сущность</th>
                <th>ID</th>
                <th>Тип</th>
                <th>Реакция</th>
                <th>Детали</th>
              </tr>
            </thead>
            <tbody>
              {issues.data.map((r) => (
                <tr key={r.id}>
                  <td>{r.entity}</td>
                  <td className="mono">{r.entity_id ?? '—'}</td>
                  <td className="mono">{r.issue_type}</td>
                  <td>
                    <ActionBadge action={r.action} />
                  </td>
                  <td>{r.details ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}

function Card({ label, value, tone }) {
  return (
    <div className={`card card-${tone}`}>
      <div className="card-value">{value}</div>
      <div className="card-label">{label}</div>
    </div>
  )
}

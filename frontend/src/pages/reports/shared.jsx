// Общие помощники страниц-отчётов: форматирование денег/процентов и обёртка
// состояний загрузки (единый вид заголовка + Loader/ErrorBox поверх useAsync).

import { ErrorBox, Loader } from '../../components.jsx'

const RUB = new Intl.NumberFormat('ru-RU', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})
const PCT = new Intl.NumberFormat('ru-RU', {
  maximumFractionDigits: 0,
  signDisplay: 'exceptZero',
})

// Деньги приходят строкой (Decimal с бэкенда) — не теряем точность. null → «—».
export function money(v) {
  if (v === null || v === undefined) return '—'
  return `${RUB.format(Number(v))} ₽`
}

// Денежное значение с подсветкой отрицательного (переплата/убыток).
export function Money({ value }) {
  if (value === null || value === undefined) return <span className="muted">—</span>
  return <span className={Number(value) < 0 ? 'neg' : ''}>{money(value)}</span>
}

// ROMI (доля) → проценты со знаком; null → «нет затрат».
export function romi(value) {
  if (value === null || value === undefined) return 'нет затрат'
  return `${PCT.format(value * 100)} %`
}

// Заголовок отчёта + лид, под ними — ошибка / лоадер / контент (render-prop).
// Заголовок виден всегда; данные держатся при повторной загрузке (см. useAsync).
export function ReportView({ title, lead, state, children }) {
  return (
    <section>
      <h1 className="page-title">{title}</h1>
      {lead && <p className="muted page-lead">{lead}</p>}
      {state.error ? (
        <ErrorBox error={state.error} />
      ) : !state.data ? (
        <Loader />
      ) : (
        children(state.data)
      )}
    </section>
  )
}

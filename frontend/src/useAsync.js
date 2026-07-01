import { useEffect, useState } from 'react'

// Маленький хук загрузки: {loading, error, data}. Отменяет установку стейта,
// если компонент размонтировался до ответа.
export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ loading: true, error: null, data: null })
  useEffect(() => {
    let alive = true
    // сохраняем прошлые данные на время повторной загрузки — не мигаем спиннером
    setState((s) => ({ loading: true, error: null, data: s.data }))
    fn()
      .then((data) => alive && setState({ loading: false, error: null, data }))
      .catch((e) => alive && setState({ loading: false, error: String(e.message || e), data: null }))
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return state
}

// Мелкие общие компоненты дашборда.

export function Loader({ label = 'Загрузка…' }) {
  return <div className="muted state-box">{label}</div>
}

export function ErrorBox({ error }) {
  return <div className="errorbox">Ошибка загрузки: {error}</div>
}

const ACTION_META = {
  fixed: { label: 'Исправлено', cls: 'badge-fixed' },
  quarantined: { label: 'Карантин', cls: 'badge-quarantined' },
  flagged: { label: 'Флаг', cls: 'badge-flagged' },
}

export function ActionBadge({ action }) {
  const m = ACTION_META[action] || { label: action, cls: 'badge-default' }
  return <span className={`badge ${m.cls}`}>{m.label}</span>
}

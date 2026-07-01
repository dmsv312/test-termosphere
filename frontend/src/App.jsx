import { useState } from 'react'
import CoreViewer from './pages/CoreViewer.jsx'
import DataQuality from './pages/DataQuality.jsx'

const TABS = [
  { key: 'quality', label: 'Качество данных' },
  { key: 'core', label: 'Просмотр core' },
]

export default function App() {
  const [tab, setTab] = useState('quality')
  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">ТС</span>
          <div>
            <div className="brand-title">ТермоСфера — аналитический контур</div>
            <div className="brand-sub">Bitrix24 → PostgreSQL → нормализация (raw→core) → отчёты</div>
          </div>
        </div>
        <nav className="tabs">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={`tab ${tab === t.key ? 'active' : ''}`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>
      <main className="content">
        {tab === 'quality' ? <DataQuality /> : <CoreViewer />}
      </main>
    </div>
  )
}

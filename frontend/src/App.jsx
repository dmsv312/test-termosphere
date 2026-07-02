import { useState } from 'react'
import CoreViewer from './pages/CoreViewer.jsx'
import DataQuality from './pages/DataQuality.jsx'
import Funnel from './pages/reports/Funnel.jsx'
import Managers from './pages/reports/Managers.jsx'
import Production from './pages/reports/Production.jsx'
import Receivables from './pages/reports/Receivables.jsx'
import Sources from './pages/reports/Sources.jsx'
import StaleDeals from './pages/reports/StaleDeals.jsx'

// Раздел «Отчёты» — страница на каждый отчёт (№7 «Проблемы данных» тоже здесь).
const REPORTS = [
  { key: 'funnel', label: 'Воронка', el: Funnel },
  { key: 'managers', label: 'Менеджеры', el: Managers },
  { key: 'receivables', label: 'Дебиторка', el: Receivables },
  { key: 'production', label: 'Производство', el: Production },
  { key: 'stale', label: 'Без активности', el: StaleDeals },
  { key: 'sources', label: 'Источники', el: Sources },
  { key: 'quality', label: 'Проблемы данных', el: DataQuality },
]

// Верхний уровень: раздел отчётов и просмотр нормализованных данных.
const SECTIONS = [
  { key: 'reports', label: 'Отчёты' },
  { key: 'core', label: 'Просмотр core' },
]

export default function App() {
  const [section, setSection] = useState('reports')
  const [report, setReport] = useState('funnel')

  const ActiveReport = (REPORTS.find((r) => r.key === report) || REPORTS[0]).el

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">ТС</span>
          <div>
            <div className="brand-title">ТермоСфера — аналитический контур</div>
            <div className="brand-sub">Аналитика продаж и производства по выгрузке из CRM</div>
          </div>
        </div>
        <nav className="tabs">
          {SECTIONS.map((s) => (
            <button
              key={s.key}
              className={`tab ${section === s.key ? 'active' : ''}`}
              onClick={() => setSection(s.key)}
            >
              {s.label}
            </button>
          ))}
        </nav>
      </header>

      {section === 'reports' && (
        <nav className="subnav">
          <div className="subnav-inner">
            {REPORTS.map((r) => (
              <button
                key={r.key}
                className={`subtab ${report === r.key ? 'active' : ''}`}
                onClick={() => setReport(r.key)}
              >
                {r.label}
              </button>
            ))}
          </div>
        </nav>
      )}

      <main className="content">
        {section === 'reports' ? <ActiveReport /> : <CoreViewer />}
      </main>
    </div>
  )
}

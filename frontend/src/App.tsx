import { useState } from 'react'
import Console from './Console'
import { useReports } from './hooks'
import ReportForm from './ReportForm'
import ReportList from './ReportList'

type View = 'engineer' | 'director'

export default function App() {
  const [view, setView] = useState<View>('engineer')

  return (
    <main>
      <header className="app-head">
        <div>
          <h1>Mission Control</h1>
          <p className="muted">Go/No-Go launch console</p>
        </div>
        <nav aria-label="View" className="switch">
          {(['engineer', 'director'] as const).map((v) => (
            <button
              key={v}
              type="button"
              className="switch-btn"
              aria-pressed={view === v}
              onClick={() => setView(v)}
            >
              {v === 'engineer' ? 'Engineer' : 'Flight Director'}
            </button>
          ))}
        </nav>
      </header>
      {view === 'engineer' ? <EngineerView /> : <Console />}
    </main>
  )
}

function EngineerView() {
  const { reports, error, reload } = useReports()

  return (
    <div className="layout">
      <ReportForm onFiled={reload} />
      <div>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <ReportList reports={reports ?? []} />
      </div>
    </div>
  )
}

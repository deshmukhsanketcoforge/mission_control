import { useEffect, useState } from 'react'
import { listReports, type Report } from './api'
import ReportForm from './ReportForm'
import ReportList from './ReportList'

export default function App() {
  const [reports, setReports] = useState<Report[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  // Bump this to reload the list, for example after a report is filed.
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    listReports()
      .then((data) => {
        if (cancelled) return
        setReports(data)
        setLoadError(null)
      })
      .catch((err) => {
        if (cancelled) return
        setLoadError(err instanceof Error ? err.message : 'Could not load reports.')
      })
    return () => {
      cancelled = true
    }
  }, [reloadKey])

  return (
    <main>
      <h1>Mission Control</h1>
      <p className="muted">Go/No-Go launch console</p>
      <div className="layout">
        <ReportForm onFiled={() => setReloadKey((k) => k + 1)} />
        <div>
          {loadError && (
            <p className="error" role="alert">
              {loadError}
            </p>
          )}
          <ReportList reports={reports} />
        </div>
      </div>
    </main>
  )
}

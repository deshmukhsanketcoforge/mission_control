import { useEffect, useState } from 'react'
import {
  getReport,
  listReports,
  type ReportDetail,
  type ReportListItem,
} from './api'

export const POLL_MS = 2000

function message(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback
}

/** The report list, refreshed every `pollMs`. `reload` fetches again right away. */
export function useReports(pollMs = POLL_MS) {
  const [reports, setReports] = useState<ReportListItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let cancelled = false
    const load = () =>
      listReports()
        .then((data) => {
          if (cancelled) return
          setReports(data)
          setError(null)
        })
        .catch((err) => {
          if (!cancelled) setError(message(err, 'Could not load reports.'))
        })
    void load()
    const timer = setInterval(load, pollMs)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [pollMs, tick])

  return { reports, error, reload: () => setTick((t) => t + 1) }
}

/** One report with its analysis and trace, refreshed every `pollMs`. */
export function useReportDetail(id: number | null, pollMs = POLL_MS) {
  const [loaded, setLoaded] = useState<ReportDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (id === null) return
    let cancelled = false
    const load = () =>
      getReport(id)
        .then((data) => {
          if (cancelled) return
          setLoaded(data)
          setError(null)
        })
        .catch((err) => {
          if (!cancelled) setError(message(err, 'Could not load the report.'))
        })
    void load()
    const timer = setInterval(load, pollMs)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [id, pollMs, tick])

  // Never show the previous report while the next one is loading.
  const detail = loaded !== null && loaded.id === id ? loaded : null
  return { detail, error, reload: () => setTick((t) => t + 1) }
}

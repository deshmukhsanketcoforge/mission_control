import { useEffect, useState } from 'react'
import {
  getReport,
  listReports,
  type ReportDetail,
  type ReportListItem,
} from './api'

export const POLL_MS = 2000

/** A report in one of these states never changes by itself, so there is nothing to poll for. */
const FINISHED = new Set(['approved', 'failed'])

function message(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback
}

/**
 * Run `load` now, then every `pollMs`, until stopped. A request never starts while the
 * previous one is running, nothing runs while the tab is hidden, and showing the tab
 * again refreshes at once. `load` returns true when polling should stop for good.
 */
function startPolling(load: () => Promise<boolean>, pollMs: number): () => void {
  let stopped = false
  let running = false
  let timer: ReturnType<typeof setInterval> | undefined

  const finish = () => {
    stopped = true
    clearInterval(timer)
  }
  const tick = async (force: boolean) => {
    if (stopped || running || (!force && document.hidden)) return
    running = true
    try {
      if (await load()) finish()
    } finally {
      running = false
    }
  }
  const onVisible = () => {
    if (!document.hidden) void tick(false)
  }

  void tick(true)
  timer = setInterval(() => void tick(false), pollMs)
  document.addEventListener('visibilitychange', onVisible)
  return () => {
    finish()
    document.removeEventListener('visibilitychange', onVisible)
  }
}

/** The report list, refreshed every `pollMs`. `reload` fetches again right away. */
export function useReports(pollMs = POLL_MS) {
  const [reports, setReports] = useState<ReportListItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let cancelled = false
    const stop = startPolling(async () => {
      try {
        const data = await listReports()
        if (cancelled) return false
        setReports(data)
        setError(null)
      } catch (err) {
        if (!cancelled) setError(message(err, 'Could not load reports.'))
      }
      return false
    }, pollMs)
    return () => {
      cancelled = true
      stop()
    }
  }, [pollMs, tick])

  return { reports, error, reload: () => setTick((t) => t + 1) }
}

/**
 * One report with its analysis and trace, refreshed every `pollMs` until it is approved or
 * failed. An error belongs to the report that caused it, so it never follows a new selection.
 */
export function useReportDetail(id: number | null, pollMs = POLL_MS) {
  const [loaded, setLoaded] = useState<ReportDetail | null>(null)
  const [failure, setFailure] = useState<{ id: number; text: string } | null>(null)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (id === null) return
    let cancelled = false
    const stop = startPolling(async () => {
      try {
        const data = await getReport(id)
        if (cancelled) return false
        setLoaded(data)
        setFailure(null)
        return FINISHED.has(data.analysis.status)
      } catch (err) {
        if (!cancelled) setFailure({ id, text: message(err, 'Could not load the report.') })
        return false
      }
    }, pollMs)
    return () => {
      cancelled = true
      stop()
    }
  }, [id, pollMs, tick])

  // Never show the previous report, or its error, while the next one is loading.
  const detail = loaded !== null && loaded.id === id ? loaded : null
  const error = failure !== null && failure.id === id ? failure.text : null
  return { detail, error, reload: () => setTick((t) => t + 1) }
}

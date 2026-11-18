import { useState } from 'react'
import CostBadge from './CostBadge'
import { statusLabel } from './format'
import { POLL_MS, useReportDetail, useReports } from './hooks'
import ReportDetail from './ReportDetail'
import VerdictBadge from './VerdictBadge'

/** The Flight Director's screen: every report, its briefing, verdict, cost and trace. */
export default function Console({ pollMs = POLL_MS }: { pollMs?: number }) {
  const list = useReports(pollMs)
  const [pickedId, setPickedId] = useState<number | null>(null)

  const reports = list.reports ?? []
  const selectedId = pickedId ?? reports[0]?.id ?? null
  const detail = useReportDetail(selectedId, pollMs)
  const waiting = reports.filter((r) => r.status === 'pending_approval').length

  return (
    <section aria-label="Flight Director console" className="console">
      <h2>Flight Director console</h2>
      <p className="muted">{waiting} awaiting approval</p>
      {list.error && (
        <p className="error" role="alert">
          {list.error}
        </p>
      )}

      <div className="console-grid">
        <div>
          {list.reports !== null && reports.length === 0 ? (
            <p className="muted">No reports yet.</p>
          ) : (
            <ul aria-label="Reports" className="report-rows">
              {reports.map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    className={`report-row${r.id === selectedId ? ' report-row--selected' : ''}`}
                    aria-current={r.id === selectedId ? 'true' : undefined}
                    onClick={() => setPickedId(r.id)}
                  >
                    <span className="row-top">
                      <strong>
                        #{r.id} {r.station}
                      </strong>
                      <VerdictBadge verdict={r.verdict} />
                    </span>
                    <span className="row-bottom">
                      <span className="chip" data-status={r.status}>
                        {statusLabel(r.status)}
                      </span>
                      {r.needs_review && <span className="chip chip--warn">Review</span>}
                      <span className="muted">
                        {r.brief_by_minutes === null ? '—' : `${r.brief_by_minutes} min`}
                      </span>
                      <CostBadge cost={r.total_cost_usd} />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <section aria-label="Report detail">
          {detail.error && (
            <p className="error" role="alert">
              {detail.error}
            </p>
          )}
          {selectedId === null ? (
            <p className="muted">Select a report.</p>
          ) : detail.detail === null ? (
            <p className="muted">Loading report…</p>
          ) : (
            <ReportDetail
              key={detail.detail.id}
              detail={detail.detail}
              onApproved={() => {
                detail.reload()
                list.reload()
              }}
            />
          )}
        </section>
      </div>
    </section>
  )
}

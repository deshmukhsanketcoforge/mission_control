import type { ReportListItem } from './api'
import { statusLabel } from './format'
import VerdictBadge from './VerdictBadge'

/** What an engineer sees after filing: each report with its verdict and status. */
export default function ReportList({ reports }: { reports: ReportListItem[] }) {
  return (
    <section aria-label="Filed reports">
      <h2>Filed reports</h2>
      {reports.length === 0 ? (
        <p className="muted">No reports yet.</p>
      ) : (
        <ul className="reports">
          {reports.map((r) => (
            <li key={r.id}>
              <div className="row-top">
                <strong>
                  #{r.id} {r.station}
                </strong>
                <VerdictBadge verdict={r.verdict} />
              </div>
              <div className="row-bottom">
                <span className="chip" data-status={r.status}>
                  {statusLabel(r.status)}
                </span>
                <span className="muted">by {r.name}</span>
              </div>
              <div className="muted">
                Wind {r.wind_knots} kt, Temp {r.temp_c} C, Fuel {r.fuel_pct}%
              </div>
              <p>{r.note}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

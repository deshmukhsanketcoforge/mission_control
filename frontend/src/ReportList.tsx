import type { Report } from './api'

export default function ReportList({ reports }: { reports: Report[] }) {
  return (
    <section aria-label="Filed reports">
      <h2>Filed reports</h2>
      {reports.length === 0 ? (
        <p className="muted">No reports yet.</p>
      ) : (
        <ul className="reports">
          {reports.map((r) => (
            <li key={r.id}>
              <strong>
                #{r.id} {r.station}
              </strong>{' '}
              <span className="muted">by {r.name}</span>
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

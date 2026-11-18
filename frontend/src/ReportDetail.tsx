import { useState } from 'react'
import { approveReport, type Check, type ReportDetail as ReportDetailData } from './api'
import CostBadge from './CostBadge'
import { reviewReasonText, statusLabel } from './format'
import TraceTimeline from './TraceTimeline'
import VerdictBadge from './VerdictBadge'

const CHECK_LABELS: Record<string, string> = {
  hidden_instructions: 'Hidden instructions',
  missing_details: 'Missing details',
  panic_tone: 'Panic in the tone',
}

interface Props {
  detail: ReportDetailData
  /** Called after a person approved, so the console can refresh. */
  onApproved: () => void
}

export default function ReportDetail({ detail, onApproved }: Props) {
  const { analysis: a, trace } = detail

  return (
    <div className="detail">
      <header className="detail-head">
        <div>
          <h3>
            #{detail.id} {detail.station}
          </h3>
          <p className="muted">Filed by {detail.name}</p>
          <p>
            Wind {detail.wind_knots} kt, Temp {detail.temp_c} C, Fuel {detail.fuel_pct}%
          </p>
        </div>
        <div className="detail-badges">
          <VerdictBadge verdict={a.verdict} />
          <span className="chip" data-status={a.status}>
            {statusLabel(a.status)}
          </span>
          <CostBadge cost={a.total_cost_usd} />
        </div>
      </header>

      {a.violations.length > 0 && (
        <ul aria-label="Limit violations" className="violations">
          {a.violations.map((v) => (
            <li key={v.field}>{v.message}</li>
          ))}
        </ul>
      )}

      <p className="facts">
        {a.brief_by_minutes !== null && <span>Brief within {a.brief_by_minutes} minutes</span>}
        {a.subsystem && <span>Subsystem: {a.subsystem}</span>}
        {a.effective_severity && <span>{severityText(a.severity, a.effective_severity)}</span>}
      </p>

      {a.needs_review && (
        <section aria-label="Needs review" className="banner">
          <h3>Needs your review</h3>
          <ul>
            {a.review_reasons.map((reason) => (
              <li key={reason}>{reviewReasonText(reason)}</li>
            ))}
          </ul>
        </section>
      )}

      <section aria-label="Briefing" className="briefing">
        <h3>Briefing</h3>
        <BriefingBody status={a.status} briefing={a.briefing} error={a.error} />
        {a.status !== 'processing' && a.briefing && a.evaluator_passed === false && (
          <p className="muted">The reviewer did not approve this draft.</p>
        )}
      </section>

      <section aria-label="Original note">
        <h3>Original note</h3>
        <p className="note">{detail.note}</p>
      </section>

      {a.checks.length > 0 && (
        <ul aria-label="Checks" className="checks">
          {a.checks.map((c) => (
            <li key={c.name}>
              <strong>{CHECK_LABELS[c.name] ?? c.name}</strong> <CheckChip check={c} />{' '}
              <span className="muted">{c.reason}</span>
            </li>
          ))}
        </ul>
      )}

      <Approval detail={detail} onApproved={onApproved} />

      <TraceTimeline steps={trace} />
    </div>
  )
}

function severityText(model: string | null, effective: string): string {
  return model && model !== effective
    ? `Severity: ${model} (briefed as ${effective})`
    : `Severity: ${effective}`
}

function CheckChip({ check }: { check: Check }) {
  if (check.failed) return <span className="chip chip--bad">Could not run</span>
  return check.flagged ? (
    <span className="chip chip--warn">Flagged</span>
  ) : (
    <span className="chip chip--ok">Clear</span>
  )
}

function BriefingBody(props: { status: string; briefing: string | null; error: string | null }) {
  if (props.status === 'processing') return <p className="muted">Drafting the briefing…</p>
  if (props.status === 'failed') {
    return <p className="error">The pipeline failed: {props.error ?? 'unknown error'}</p>
  }
  if (!props.briefing?.trim()) return <p className="muted">No briefing was drafted for this report.</p>
  return <p>{props.briefing}</p>
}

function Approval({ detail, onApproved }: Props) {
  const a = detail.analysis
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (a.status === 'approved') {
    return (
      <section aria-label="Approval" className="approval">
        <p>
          Approved by {a.approved_by}
          {a.approved_at ? ` on ${new Date(a.approved_at).toLocaleString()}` : ''}
        </p>
      </section>
    )
  }
  if (a.status !== 'pending_approval') return null

  async function approve(e: React.FormEvent) {
    e.preventDefault()
    if (busy || !name.trim()) return
    setBusy(true)
    setError(null)
    try {
      await approveReport(detail.id, name.trim())
      onApproved()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not approve the report.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section aria-label="Approval" className="approval">
      <form onSubmit={approve}>
        <div className="field">
          <label htmlFor="approver">Your name</label>
          <input id="approver" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <button type="submit" disabled={busy || !name.trim()}>
          Approve briefing
        </button>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
      </form>
    </section>
  )
}

export interface ReportInput {
  name: string
  station: string
  wind_knots: number
  temp_c: number
  fuel_pct: number
  note: string
}

export interface Report extends ReportInput {
  id: number
  created_at: string
}

export type FieldErrors = Partial<Record<keyof ReportInput | 'form', string>>

export class ValidationError extends Error {
  errors: FieldErrors
  constructor(errors: FieldErrors) {
    super('Validation failed')
    this.errors = errors
  }
}

export async function fileReport(input: ReportInput): Promise<Report> {
  const res = await fetch('/api/reports', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (res.status === 422) {
    const body = await res.json()
    throw new ValidationError(body.errors ?? { form: 'The report was rejected.' })
  }
  if (!res.ok) throw new Error(`Could not save the report (HTTP ${res.status}).`)
  return res.json()
}

export interface Violation {
  field: string
  value: number
  limit: string
  message: string
}

export interface Check {
  name: string
  flagged: boolean
  reason: string
  failed: boolean
}

export interface TraceStep {
  seq: number
  step: string
  round: number | null
  model: string | null // null for steps done in plain code
  input_tokens: number
  output_tokens: number
  latency_ms: number
  cost_usd: string // exact decimal text from the server
  status: string
  detail: string
}

export interface Analysis {
  status: string
  verdict: string
  violations: Violation[]
  subsystem: string | null
  severity: string | null
  effective_severity: string | null
  brief_by_minutes: number | null
  checks: Check[]
  needs_review: boolean
  review_reasons: string[]
  briefing: string | null
  evaluator_passed: boolean | null
  rounds: number
  total_cost_usd: string
  error: string | null
  approved_by: string | null
  approved_at: string | null
}

export interface ReportListItem extends Report {
  status: string
  verdict: string
  brief_by_minutes: number | null
  needs_review: boolean
  total_cost_usd: string
}

export interface ReportDetail extends Report {
  analysis: Analysis
  trace: TraceStep[]
}

/** An error whose message came from the server and is safe to show. */
export class ApiError extends Error {}

async function serverMessage(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json()
    const first = Object.values(body?.errors ?? {})[0]
    if (typeof first === 'string') return first
  } catch {
    // not JSON: use the fallback
  }
  return fallback
}

export async function listReports(): Promise<ReportListItem[]> {
  const res = await fetch('/api/reports')
  if (!res.ok) throw new Error(`Could not load reports (HTTP ${res.status}).`)
  return res.json()
}

export async function getReport(id: number): Promise<ReportDetail> {
  const res = await fetch(`/api/reports/${id}`)
  if (!res.ok) {
    throw new ApiError(await serverMessage(res, `Could not load the report (HTTP ${res.status}).`))
  }
  return res.json()
}

/** Only a person calls this, from the approve button. */
export async function approveReport(id: number, approvedBy: string): Promise<Analysis> {
  const res = await fetch(`/api/reports/${id}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approved_by: approvedBy }),
  })
  if (!res.ok) {
    throw new ApiError(
      await serverMessage(res, `Could not approve the report (HTTP ${res.status}).`),
    )
  }
  return res.json()
}

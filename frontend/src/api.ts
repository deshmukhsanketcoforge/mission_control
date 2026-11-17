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

export async function listReports(): Promise<Report[]> {
  const res = await fetch('/api/reports')
  if (!res.ok) throw new Error(`Could not load reports (HTTP ${res.status}).`)
  return res.json()
}

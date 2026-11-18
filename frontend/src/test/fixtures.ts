import type { Analysis, ReportDetail, ReportListItem, TraceStep } from '../api'

export function makeStep(overrides: Partial<TraceStep> = {}): TraceStep {
  return {
    seq: 0,
    step: 'sort',
    round: null,
    model: 'claude-haiku-5-5',
    input_tokens: 1000,
    output_tokens: 500,
    latency_ms: 1241,
    cost_usd: '0.00035',
    status: 'ok',
    detail: 'propulsion / medium',
    ...overrides,
  }
}

/** The steps of a clean one-round report, as the server returns them. */
export function makeTrace(): TraceStep[] {
  const code = { model: null, input_tokens: 0, output_tokens: 0, latency_ms: 0, cost_usd: '0' }
  return [
    makeStep({ seq: 0, step: 'limits', detail: 'go; 0 violations', ...code }),
    makeStep({ seq: 1, step: 'sort' }),
    makeStep({ seq: 2, step: 'check_injection', input_tokens: 100, output_tokens: 10, cost_usd: '0.000015', detail: 'not flagged: Nothing found.' }),
    makeStep({ seq: 3, step: 'check_missing', input_tokens: 100, output_tokens: 10, cost_usd: '0.000015', detail: 'not flagged: Nothing found.' }),
    makeStep({ seq: 4, step: 'check_panic', input_tokens: 100, output_tokens: 10, cost_usd: '0.000015', detail: 'not flagged: Nothing found.' }),
    makeStep({ seq: 5, step: 'brief_by', detail: '15 minutes (medium severity)', ...code }),
    makeStep({ seq: 6, step: 'draft', round: 1, model: 'claude-sonnet-5-5', input_tokens: 1000, output_tokens: 200, cost_usd: '0.004', detail: 'Round 1' }),
    makeStep({ seq: 7, step: 'review', round: 1, model: 'claude-sonnet-5-5', input_tokens: 500, output_tokens: 50, cost_usd: '0.0015', detail: 'approved' }),
  ]
}

export function makeAnalysis(overrides: Partial<Analysis> = {}): Analysis {
  return {
    status: 'pending_approval',
    verdict: 'go',
    violations: [],
    subsystem: 'propulsion',
    severity: 'medium',
    effective_severity: 'medium',
    brief_by_minutes: 15,
    checks: [
      { name: 'hidden_instructions', flagged: false, reason: 'Nothing found.', failed: false },
      { name: 'missing_details', flagged: false, reason: 'Nothing found.', failed: false },
      { name: 'panic_tone', flagged: false, reason: 'Nothing found.', failed: false },
    ],
    needs_review: false,
    review_reasons: [],
    briefing: 'Valve V3 stuck briefly. Verdict GO. Check actuation data first.',
    evaluator_passed: true,
    rounds: 1,
    total_cost_usd: '0.005895',
    error: null,
    approved_by: null,
    approved_at: null,
    ...overrides,
  }
}

export function makeDetail(overrides: Partial<ReportDetail> = {}): ReportDetail {
  return {
    id: 1,
    name: 'Ada Lovelace',
    station: 'Propulsion-2',
    wind_knots: 12,
    temp_c: 18,
    fuel_pct: 99,
    note: 'Valve V3 stuck for two seconds before opening.',
    created_at: '2026-11-17T01:00:00Z',
    analysis: makeAnalysis(),
    trace: makeTrace(),
    ...overrides,
  }
}

export function makeItem(overrides: Partial<ReportListItem> = {}): ReportListItem {
  return {
    id: 1,
    name: 'Ada Lovelace',
    station: 'Propulsion-2',
    wind_knots: 12,
    temp_c: 18,
    fuel_pct: 99,
    note: 'Valve V3 stuck for two seconds before opening.',
    created_at: '2026-11-17T01:00:00Z',
    status: 'pending_approval',
    verdict: 'go',
    brief_by_minutes: 15,
    needs_review: false,
    total_cost_usd: '0.005895',
    ...overrides,
  }
}

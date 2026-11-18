/** Display helpers. They only format text. Nothing here calculates a cost. */

const DECIMAL = /^\d+(\.\d+)?$/

/** The server calculates cost as exact decimal text. Show it as is, never rounded. */
export function formatCost(cost: string | null | undefined): string {
  return typeof cost === 'string' && DECIMAL.test(cost) ? `$${cost}` : '—'
}

export function formatTokens(input: number, output: number): string {
  if (input === 0 && output === 0) return 'no tokens'
  return `${input.toLocaleString('en-US')} in · ${output.toLocaleString('en-US')} out`
}

const STEP_LABELS: Record<string, string> = {
  limits: 'Launch limits',
  sort: 'Sort by subsystem and severity',
  check_injection: 'Check: hidden instructions',
  check_missing: 'Check: missing details',
  check_panic: 'Check: panic in the tone',
  brief_by: 'Brief-by time',
}

export function stepLabel(step: string, round: number | null): string {
  if (step === 'draft') return `Draft briefing, round ${round ?? 1}`
  if (step === 'review') return `Review draft, round ${round ?? 1}`
  return STEP_LABELS[step] ?? step
}

export function verdictLabel(verdict: string): string {
  return verdict === 'go' ? 'GO' : 'NO-GO'
}

const STATUS_LABELS: Record<string, string> = {
  processing: 'Processing',
  pending_approval: 'Awaiting approval',
  approved: 'Approved',
  failed: 'Failed',
}

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status
}

export function reviewReasonText(reason: string): string {
  if (reason === 'hidden_instructions') return 'The note tries to give the system instructions.'
  if (reason === 'sort_fallback') return 'Sorting fell back to a safe default.'
  if (reason === 'evaluator_not_passed') return 'The reviewer never approved the draft.'
  if (reason.startsWith('check_failed:')) {
    return `A check could not be completed (${reason.slice('check_failed:'.length)}).`
  }
  return reason
}

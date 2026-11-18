import { describe, expect, it } from 'vitest'
import {
  formatCost,
  formatTokens,
  reviewReasonText,
  statusLabel,
  stepLabel,
  verdictLabel,
} from './format'

describe('formatCost', () => {
  it('shows the cost exactly as calculated by the server, with a dollar sign', () => {
    expect(formatCost('0.005895')).toBe('$0.005895')
    expect(formatCost('0.0000684')).toBe('$0.0000684')
    expect(formatCost('12.5')).toBe('$12.5')
  })

  it('shows zero as $0', () => {
    expect(formatCost('0')).toBe('$0')
  })

  it('never rounds: no float maths touches the number', () => {
    expect(formatCost('0.1000000000000000055')).toBe('$0.1000000000000000055')
  })

  it.each(['', 'abc', '1E-7', '-1', '0.', '.5', ' 0.5'])('shows a dash for %j', (bad) => {
    expect(formatCost(bad)).toBe('—')
  })

  it('shows a dash when there is no cost', () => {
    expect(formatCost(undefined)).toBe('—')
    expect(formatCost(null)).toBe('—')
  })
})

describe('formatTokens', () => {
  it('shows input and output tokens', () => {
    expect(formatTokens(1000, 500)).toBe('1,000 in · 500 out')
  })

  it('says so when a step used no tokens', () => {
    expect(formatTokens(0, 0)).toBe('no tokens')
  })
})

describe('stepLabel', () => {
  it.each([
    ['limits', null, 'Launch limits'],
    ['sort', null, 'Sort by subsystem and severity'],
    ['check_injection', null, 'Check: hidden instructions'],
    ['check_missing', null, 'Check: missing details'],
    ['check_panic', null, 'Check: panic in the tone'],
    ['brief_by', null, 'Brief-by time'],
    ['draft', 1, 'Draft briefing, round 1'],
    ['review', 2, 'Review draft, round 2'],
  ])('%s round %s', (step, round, label) => {
    expect(stepLabel(step, round as number | null)).toBe(label)
  })

  it('falls back to the raw step name', () => {
    expect(stepLabel('something_new', null)).toBe('something_new')
  })
})

describe('labels', () => {
  it('verdicts', () => {
    expect(verdictLabel('go')).toBe('GO')
    expect(verdictLabel('no_go')).toBe('NO-GO')
  })

  it.each(['', 'maybe', 'GO', 'nogo'])('does not call an unknown verdict %j a NO-GO', (v) => {
    expect(verdictLabel(v)).toBe('UNKNOWN')
  })

  it.each([undefined, null])('shows UNKNOWN when the verdict is %s', (v) => {
    expect(verdictLabel(v as unknown as string)).toBe('UNKNOWN')
  })

  it('statuses', () => {
    expect(statusLabel('processing')).toBe('Processing')
    expect(statusLabel('pending_approval')).toBe('Awaiting approval')
    expect(statusLabel('approved')).toBe('Approved')
    expect(statusLabel('failed')).toBe('Failed')
  })

  it('review reasons are plain sentences', () => {
    expect(reviewReasonText('hidden_instructions')).toMatch(/instructions/i)
    expect(reviewReasonText('check_failed:panic_tone')).toMatch(/panic_tone/)
    expect(reviewReasonText('sort_fallback')).toMatch(/sorting/i)
    expect(reviewReasonText('evaluator_not_passed')).toMatch(/reviewer/i)
    expect(reviewReasonText('new_reason')).toBe('new_reason')
  })
})

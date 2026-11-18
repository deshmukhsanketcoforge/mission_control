import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import CostBadge from './CostBadge'
import TraceCard from './TraceCard'
import TraceTimeline from './TraceTimeline'
import VerdictBadge from './VerdictBadge'
import { makeStep, makeTrace } from './test/fixtures'

describe('TraceCard', () => {
  it('shows the step name, model, tokens, time and cost', () => {
    render(<TraceCard step={makeStep()} />)
    const card = screen.getByRole('article', { name: 'Sort by subsystem and severity' })

    expect(within(card).getByText('claude-haiku-5-5')).toBeInTheDocument()
    expect(within(card).getByText('1,000 in · 500 out')).toBeInTheDocument()
    expect(within(card).getByText('1,241 ms')).toBeInTheDocument()
    expect(within(card).getByText('$0.00035')).toBeInTheDocument()
    expect(within(card).getByText('propulsion / medium')).toBeInTheDocument()
  })

  it('names the round on draft and review cards', () => {
    render(<TraceCard step={makeStep({ step: 'draft', round: 2, model: 'claude-sonnet-5-5' })} />)
    expect(screen.getByRole('article', { name: 'Draft briefing, round 2' })).toBeInTheDocument()
  })

  it('shows steps done in plain code as code, with no tokens and no cost', () => {
    const step = makeStep({
      step: 'limits', model: null, input_tokens: 0, output_tokens: 0, latency_ms: 0, cost_usd: '0',
    })
    render(<TraceCard step={step} />)
    const card = screen.getByRole('article', { name: 'Launch limits' })

    expect(within(card).getByText('plain code')).toBeInTheDocument()
    expect(within(card).getByText('no tokens')).toBeInTheDocument()
    expect(within(card).getByText('$0')).toBeInTheDocument()
  })

  it('marks a step that failed', () => {
    render(<TraceCard step={makeStep({ status: 'error', detail: 'service down' })} />)
    const card = screen.getByRole('article')
    expect(within(card).getByText('Failed')).toBeInTheDocument()
    expect(within(card).getByText('service down')).toBeInTheDocument()
  })

  it('does not mark a step that worked', () => {
    render(<TraceCard step={makeStep()} />)
    expect(screen.queryByText('Failed')).not.toBeInTheDocument()
  })
})

describe('TraceTimeline', () => {
  it('shows one card per step', () => {
    const trace = makeTrace()
    render(<TraceTimeline steps={trace} />)
    expect(screen.getAllByRole('article')).toHaveLength(trace.length)
  })

  it('keeps the steps in the order they ran', () => {
    render(<TraceTimeline steps={makeTrace()} />)
    const names = screen.getAllByRole('article').map((a) => a.getAttribute('aria-label'))
    expect(names).toEqual([
      'Launch limits',
      'Sort by subsystem and severity',
      'Check: hidden instructions',
      'Check: missing details',
      'Check: panic in the tone',
      'Brief-by time',
      'Draft briefing, round 1',
      'Review draft, round 1',
    ])
  })

  it('shows a card for every round when the draft was revised', () => {
    const steps = [
      ...makeTrace(),
      makeStep({ seq: 8, step: 'draft', round: 2 }),
      makeStep({ seq: 9, step: 'review', round: 2 }),
    ]
    render(<TraceTimeline steps={steps} />)
    expect(screen.getAllByRole('article')).toHaveLength(10)
    expect(screen.getByRole('article', { name: 'Draft briefing, round 2' })).toBeInTheDocument()
  })

  it('says when there are no steps yet', () => {
    render(<TraceTimeline steps={[]} />)
    expect(screen.getByText('No steps yet.')).toBeInTheDocument()
    expect(screen.queryByRole('article')).not.toBeInTheDocument()
  })
})

describe('CostBadge', () => {
  it('shows the cost exactly as the server calculated it', () => {
    render(<CostBadge cost="0.005895" />)
    expect(screen.getByText('$0.005895')).toBeInTheDocument()
    expect(screen.getByLabelText('Cost')).toBeInTheDocument()
  })

  it('shows zero cost', () => {
    render(<CostBadge cost="0" />)
    expect(screen.getByText('$0')).toBeInTheDocument()
  })

  it('shows a dash instead of a made-up number when the cost is unusable', () => {
    render(<CostBadge cost="oops" />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('shows the same total as the sum shown on the cards', () => {
    // The server adds the step costs. The UI must show that total, not its own.
    render(
      <>
        <TraceTimeline steps={makeTrace()} />
        <CostBadge cost="0.005895" />
      </>,
    )
    expect(screen.getByLabelText('Cost')).toHaveTextContent('$0.005895')
  })
})

describe('VerdictBadge', () => {
  it('shows GO', () => {
    render(<VerdictBadge verdict="go" />)
    const badge = screen.getByLabelText('Verdict')
    expect(badge).toHaveTextContent('GO')
    expect(badge).toHaveAttribute('data-verdict', 'go')
  })

  it('shows NO-GO', () => {
    render(<VerdictBadge verdict="no_go" />)
    const badge = screen.getByLabelText('Verdict')
    expect(badge).toHaveTextContent('NO-GO')
    expect(badge).toHaveAttribute('data-verdict', 'no_go')
  })
})

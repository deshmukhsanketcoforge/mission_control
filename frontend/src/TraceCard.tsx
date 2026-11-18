import type { TraceStep } from './api'
import { formatCost, formatTokens, stepLabel } from './format'

export default function TraceCard({ step }: { step: TraceStep }) {
  const label = stepLabel(step.step, step.round)
  const failed = step.status === 'error'
  const isCode = step.model === null

  return (
    <article className={`trace-card${failed ? ' trace-card--error' : ''}`} aria-label={label}>
      <header>
        <span className="trace-seq" aria-hidden="true">
          {step.seq + 1}
        </span>
        <h4>{label}</h4>
        {failed && <span className="chip chip--bad">Failed</span>}
      </header>
      <dl className="trace-meta">
        <div>
          <dt>Model</dt>
          <dd>{isCode ? 'plain code' : step.model}</dd>
        </div>
        <div>
          <dt>Tokens</dt>
          <dd>{formatTokens(step.input_tokens, step.output_tokens)}</dd>
        </div>
        {!isCode && (
          <div>
            <dt>Time</dt>
            <dd>{step.latency_ms.toLocaleString('en-US')} ms</dd>
          </div>
        )}
        <div>
          <dt>Cost</dt>
          <dd>{formatCost(step.cost_usd)}</dd>
        </div>
      </dl>
      {step.detail && <p className="trace-detail">{step.detail}</p>}
    </article>
  )
}

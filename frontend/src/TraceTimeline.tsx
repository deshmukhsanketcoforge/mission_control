import type { TraceStep } from './api'
import TraceCard from './TraceCard'

/** One card per step, in the order the steps ran. */
export default function TraceTimeline({ steps }: { steps: TraceStep[] }) {
  return (
    <section aria-label="Trace" className="trace">
      <h3>Trace</h3>
      {steps.length === 0 ? (
        <p className="muted">No steps yet.</p>
      ) : (
        <ol className="trace-list">
          {steps.map((step) => (
            <li key={step.seq}>
              <TraceCard step={step} />
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

import { formatCost } from './format'

/** Shows the cost the server calculated. It never calculates or rounds. */
export default function CostBadge({ cost }: { cost: string }) {
  return (
    <span className="cost" aria-label="Cost">
      <span className="muted">Cost</span> <strong>{formatCost(cost)}</strong>
    </span>
  )
}

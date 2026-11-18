import { verdictLabel } from './format'

export default function VerdictBadge({ verdict }: { verdict: string }) {
  return (
    <span className="verdict" aria-label="Verdict" data-verdict={verdict}>
      {verdictLabel(verdict)}
    </span>
  )
}

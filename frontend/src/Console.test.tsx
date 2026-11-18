import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Console from './Console'
import { makeAnalysis, makeDetail, makeItem, makeTrace } from './test/fixtures'
import type { ReportDetail, ReportListItem } from './api'

const fetchMock = vi.fn()

let items: ReportListItem[] = []
let details: Record<number, ReportDetail> = {}
let failList = false

const json = (status: number, body: unknown) => ({
  status,
  ok: status >= 200 && status < 300,
  json: async () => body,
})

beforeEach(() => {
  items = []
  details = {}
  failList = false
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    if (init?.method === 'POST' && url.endsWith('/approve')) {
      const id = Number(url.split('/')[3])
      const body = JSON.parse(String(init.body))
      details[id] = makeDetail({
        ...details[id],
        analysis: { ...details[id].analysis, status: 'approved', approved_by: body.approved_by },
      })
      items = items.map((i) => (i.id === id ? { ...i, status: 'approved' } : i))
      return json(200, details[id].analysis)
    }
    if (url === '/api/reports') return failList ? json(500, {}) : json(200, items)
    const id = Number(url.split('/').pop())
    return details[id] ? json(200, details[id]) : json(404, { errors: { report: 'Report not found.' } })
  })
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => fetchMock.mockReset())

function add(id: number, station: string, overrides: Partial<ReportListItem> = {}, analysis = {}) {
  const item = makeItem({ id, station, ...overrides })
  items = [item, ...items.filter((i) => i.id !== id)].sort((a, b) => b.id - a.id)
  details[id] = makeDetail({
    id,
    station,
    note: `Note for ${station}`,
    analysis: makeAnalysis({
      status: item.status,
      verdict: item.verdict,
      total_cost_usd: item.total_cost_usd,
      briefing: `Briefing for ${station}`,
      ...analysis,
    }),
    trace: makeTrace(),
  })
}

describe('the report list', () => {
  it('says when there are no reports', async () => {
    render(<Console pollMs={30} />)
    expect(await screen.findByText('No reports yet.')).toBeInTheDocument()
  })

  it('lists each report with verdict, status, brief-by time and cost', async () => {
    add(1, 'Propulsion-2')
    add(2, 'Pad-1', { verdict: 'no_go', brief_by_minutes: 5, total_cost_usd: '0.0117136' })
    render(<Console pollMs={30} />)

    const list = await screen.findByRole('list', { name: 'Reports' })
    const row = within(list).getByRole('button', { name: /Pad-1/ })
    expect(within(row).getByLabelText('Verdict')).toHaveTextContent('NO-GO')
    expect(within(row).getByText('Awaiting approval')).toBeInTheDocument()
    expect(within(row).getByText('5 min')).toBeInTheDocument()
    expect(within(row).getByText('$0.0117136')).toBeInTheDocument()
  })

  it('marks reports that need review', async () => {
    add(1, 'Propulsion-2', { needs_review: true })
    add(2, 'Pad-1')
    render(<Console pollMs={30} />)

    const list = await screen.findByRole('list', { name: 'Reports' })
    expect(within(within(list).getByRole('button', { name: /Propulsion-2/ })).getByText('Review')).toBeInTheDocument()
    expect(within(within(list).getByRole('button', { name: /Pad-1/ })).queryByText('Review')).not.toBeInTheDocument()
  })

  it('counts the briefings waiting for a decision', async () => {
    add(1, 'A')
    add(2, 'B', { status: 'approved' })
    add(3, 'C')
    add(4, 'D', { status: 'processing' })
    render(<Console pollMs={30} />)
    expect(await screen.findByText('2 awaiting approval')).toBeInTheDocument()
  })

  it('shows an error when the reports cannot be loaded', async () => {
    failList = true
    render(<Console pollMs={30} />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/Could not load reports/)
  })
})

describe('the report detail', () => {
  it('opens the newest report first', async () => {
    add(1, 'Propulsion-2')
    add(2, 'Pad-1')
    render(<Console pollMs={30} />)

    const detail = await screen.findByRole('region', { name: 'Report detail' })
    expect(await within(detail).findByText('Briefing for Pad-1')).toBeInTheDocument()
    expect(within(detail).getAllByRole('article')).toHaveLength(8)
  })

  it('opens another report when it is clicked', async () => {
    const user = userEvent.setup()
    add(1, 'Propulsion-2')
    add(2, 'Pad-1')
    render(<Console pollMs={30} />)

    await screen.findByText('Briefing for Pad-1')
    await user.click(screen.getByRole('button', { name: /Propulsion-2/ }))

    expect(await screen.findByText('Briefing for Propulsion-2')).toBeInTheDocument()
    expect(screen.queryByText('Briefing for Pad-1')).not.toBeInTheDocument()
  })

  it('does not show the previous report while the next one loads', async () => {
    const user = userEvent.setup()
    add(1, 'Propulsion-2')
    add(2, 'Pad-1')
    render(<Console pollMs={30} />)
    await screen.findByText('Briefing for Pad-1')

    await user.click(screen.getByRole('button', { name: /Propulsion-2/ }))
    expect(screen.queryByText('Briefing for Pad-1')).not.toBeInTheDocument()
  })
})

describe('the selected report stays put', () => {
  it('keeps the same report open when a newer one is filed while nothing was clicked', async () => {
    add(1, 'Propulsion-2')
    render(<Console pollMs={30} />)
    await screen.findByText('Briefing for Propulsion-2')

    add(2, 'Pad-1')
    await screen.findByRole('button', { name: /Pad-1/ })
    await new Promise((r) => setTimeout(r, 120))

    expect(screen.getByText('Briefing for Propulsion-2')).toBeInTheDocument()
    expect(screen.queryByText('Briefing for Pad-1')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Propulsion-2/ })).toHaveAttribute('aria-current', 'true')
  })

  it('does not lose a half-typed approval name when a new report arrives', async () => {
    const user = userEvent.setup()
    add(1, 'Propulsion-2')
    render(<Console pollMs={30} />)
    await screen.findByText('Briefing for Propulsion-2')
    await user.type(screen.getByLabelText('Your name'), 'Dana')

    add(2, 'Pad-1')
    await screen.findByRole('button', { name: /Pad-1/ })
    await new Promise((r) => setTimeout(r, 120))

    expect(screen.getByLabelText('Your name')).toHaveValue('Dana')
  })

  it('opens the newest report only on the first load', async () => {
    add(1, 'A')
    add(2, 'B')
    render(<Console pollMs={30} />)
    expect(await screen.findByText('Briefing for B')).toBeInTheDocument()
    add(3, 'C')
    await screen.findByRole('button', { name: /#3 C/ })
    await new Promise((r) => setTimeout(r, 100))
    expect(screen.getByText('Briefing for B')).toBeInTheDocument()
  })

  it('picks the first report when the list starts empty and fills later', async () => {
    render(<Console pollMs={30} />)
    await screen.findByText('No reports yet.')
    add(1, 'Propulsion-2')
    expect(await screen.findByText('Briefing for Propulsion-2')).toBeInTheDocument()
  })
})

describe('keeping up with new reports', () => {
  it('shows a report that is filed after the page opened', async () => {
    add(1, 'Propulsion-2')
    render(<Console pollMs={30} />)
    await screen.findByRole('button', { name: /Propulsion-2/ })

    add(2, 'Pad-1')
    expect(await screen.findByRole('button', { name: /Pad-1/ })).toBeInTheDocument()
  })

  it('updates a report as the pipeline finishes it', async () => {
    add(1, 'Propulsion-2', { status: 'processing' }, { briefing: null })
    render(<Console pollMs={30} />)
    expect(await screen.findByText(/Drafting the briefing/)).toBeInTheDocument()

    add(1, 'Propulsion-2', { status: 'pending_approval' })
    expect(await screen.findByText('Briefing for Propulsion-2')).toBeInTheDocument()
    expect(screen.queryByText(/Drafting the briefing/)).not.toBeInTheDocument()
  })

  it('stops asking the server once it is closed', async () => {
    add(1, 'Propulsion-2')
    const { unmount } = render(<Console pollMs={20} />)
    await screen.findByRole('button', { name: /Propulsion-2/ })
    unmount()

    const calls = fetchMock.mock.calls.length
    await new Promise((r) => setTimeout(r, 120))
    expect(fetchMock.mock.calls.length).toBe(calls)
  })
})

describe('approving from the console', () => {
  it('approves, then shows who approved it', async () => {
    const user = userEvent.setup()
    add(1, 'Propulsion-2')
    render(<Console pollMs={30} />)

    await screen.findByText('Briefing for Propulsion-2')
    await user.type(screen.getByLabelText('Your name'), 'Dana Reyes')
    await user.click(screen.getByRole('button', { name: 'Approve briefing' }))

    expect(await screen.findByText(/Approved by Dana Reyes/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Approve briefing' })).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('0 awaiting approval')).toBeInTheDocument())
  })

  it('never approves without a click: loading a report does not call approve', async () => {
    add(1, 'Propulsion-2')
    render(<Console pollMs={30} />)
    await screen.findByText('Briefing for Propulsion-2')
    await new Promise((r) => setTimeout(r, 100))

    const approvals = fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST')
    expect(approvals).toHaveLength(0)
  })
})

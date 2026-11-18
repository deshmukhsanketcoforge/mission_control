import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { makeAnalysis, makeDetail, makeItem } from './test/fixtures'

const fetchMock = vi.fn()
const json = (body: unknown, status = 200) => ({ status, ok: status < 300, json: async () => body })

beforeEach(() => {
  fetchMock.mockImplementation(async (url: string) => {
    if (url === '/api/reports') {
      return json([makeItem({ id: 1, station: 'Pad-1', verdict: 'no_go', status: 'pending_approval' })])
    }
    return json(makeDetail({ id: 1, station: 'Pad-1', analysis: makeAnalysis({ verdict: 'no_go' }) }))
  })
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => fetchMock.mockReset())

describe('switching between the two views', () => {
  it('opens on the engineer view with the filing form', async () => {
    render(<App />)
    expect(screen.getByRole('form', { name: 'File an anomaly report' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Flight Director console' })).not.toBeInTheDocument()
  })

  it('shows the Flight Director console when that view is chosen', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Flight Director' }))

    expect(screen.getByRole('heading', { name: 'Flight Director console' })).toBeInTheDocument()
    expect(screen.queryByRole('form', { name: 'File an anomaly report' })).not.toBeInTheDocument()
    expect(await screen.findByRole('region', { name: 'Report detail' })).toBeInTheDocument()
  })

  it('can switch back to the engineer view', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Flight Director' }))
    await user.click(screen.getByRole('button', { name: 'Engineer' }))
    expect(screen.getByRole('form', { name: 'File an anomaly report' })).toBeInTheDocument()
  })

  it('marks which view is open', async () => {
    const user = userEvent.setup()
    render(<App />)
    expect(screen.getByRole('button', { name: 'Engineer' })).toHaveAttribute('aria-pressed', 'true')
    await user.click(screen.getByRole('button', { name: 'Flight Director' }))
    expect(screen.getByRole('button', { name: 'Flight Director' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Engineer' })).toHaveAttribute('aria-pressed', 'false')
  })
})

describe('the engineer view', () => {
  it('shows each filed report with its verdict and status', async () => {
    render(<App />)
    const list = await screen.findByRole('region', { name: 'Filed reports' })
    expect(await within(list).findByLabelText('Verdict')).toHaveTextContent('NO-GO')
    expect(within(list).getByText('Awaiting approval')).toBeInTheDocument()
  })

  it('cannot approve anything', async () => {
    render(<App />)
    await screen.findByRole('region', { name: 'Filed reports' })
    expect(screen.queryByRole('button', { name: 'Approve briefing' })).not.toBeInTheDocument()
  })
})

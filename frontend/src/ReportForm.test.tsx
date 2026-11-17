import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ReportForm from './ReportForm'

const fetchMock = vi.fn()

beforeEach(() => vi.stubGlobal('fetch', fetchMock))
afterEach(() => fetchMock.mockReset())

async function fillAll(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText('Your name'), 'Ada')
  await user.type(screen.getByLabelText('Station'), 'Propulsion-2')
  await user.type(screen.getByLabelText('Wind (knots)'), '12.5')
  await user.type(screen.getByLabelText('Temperature (C)'), '18')
  await user.type(screen.getByLabelText('Fuel (%)'), '99.2')
  await user.type(screen.getByLabelText('Note'), 'Valve stuck briefly')
}

describe('ReportForm', () => {
  it('sends every field to the API', async () => {
    const user = userEvent.setup()
    const onFiled = vi.fn()
    fetchMock.mockResolvedValue({ status: 201, ok: true, json: async () => ({ id: 1 }) })
    render(<ReportForm onFiled={onFiled} />)

    await fillAll(user)
    await user.click(screen.getByRole('button', { name: 'File report' }))

    await waitFor(() => expect(onFiled).toHaveBeenCalled())
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/reports')
    expect(JSON.parse(init.body)).toEqual({
      name: 'Ada',
      station: 'Propulsion-2',
      wind_knots: 12.5,
      temp_c: 18,
      fuel_pct: 99.2,
      note: 'Valve stuck briefly',
    })
  })

  it('shows a message for each empty field and does not call the API', async () => {
    const user = userEvent.setup()
    render(<ReportForm onFiled={vi.fn()} />)

    await user.click(screen.getByRole('button', { name: 'File report' }))

    expect(screen.getAllByText('This field is required.')).toHaveLength(6)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('shows the server message next to the field it belongs to', async () => {
    const user = userEvent.setup()
    fetchMock.mockResolvedValue({
      status: 422,
      ok: false,
      json: async () => ({ errors: { fuel_pct: 'Fuel must be between 0 and 100 percent.' } }),
    })
    render(<ReportForm onFiled={vi.fn()} />)

    await fillAll(user)
    await user.click(screen.getByRole('button', { name: 'File report' }))

    const alert = await screen.findByText('Fuel must be between 0 and 100 percent.')
    expect(alert).toHaveAttribute('id', 'fuel_pct-error')
    expect(screen.getByLabelText('Fuel (%)')).toHaveAttribute('aria-invalid', 'true')
  })

  it('shows a general message when the server is unreachable', async () => {
    const user = userEvent.setup()
    fetchMock.mockResolvedValue({ status: 500, ok: false, json: async () => ({}) })
    render(<ReportForm onFiled={vi.fn()} />)

    await fillAll(user)
    await user.click(screen.getByRole('button', { name: 'File report' }))

    expect(await screen.findByText(/Could not save the report/)).toBeInTheDocument()
  })
})

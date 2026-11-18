import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, approveReport, getReport, listReports } from './api'

const fetchMock = vi.fn()
beforeEach(() => vi.stubGlobal('fetch', fetchMock))
afterEach(() => fetchMock.mockReset())

const reply = (status: number, body: unknown) => ({
  status,
  ok: status >= 200 && status < 300,
  json: async () => body,
})

describe('listReports', () => {
  it('returns the list items with status, verdict and cost', async () => {
    fetchMock.mockResolvedValue(reply(200, [{ id: 1, status: 'approved', verdict: 'go' }]))
    const items = await listReports()
    expect(items[0].verdict).toBe('go')
    expect(fetchMock).toHaveBeenCalledWith('/api/reports')
  })

  it('throws a readable error when the server fails', async () => {
    fetchMock.mockResolvedValue(reply(500, {}))
    await expect(listReports()).rejects.toThrow(/Could not load reports/)
  })
})

describe('getReport', () => {
  it('loads one report with its analysis and trace', async () => {
    fetchMock.mockResolvedValue(reply(200, { id: 7, analysis: {}, trace: [] }))
    expect((await getReport(7)).id).toBe(7)
    expect(fetchMock).toHaveBeenCalledWith('/api/reports/7')
  })

  it('says when the report does not exist', async () => {
    fetchMock.mockResolvedValue(reply(404, { errors: { report: 'Report not found.' } }))
    await expect(getReport(9)).rejects.toThrow('Report not found.')
  })
})

describe('approveReport', () => {
  it('posts the name of the person approving', async () => {
    fetchMock.mockResolvedValue(reply(200, { status: 'approved', approved_by: 'Dana' }))
    const result = await approveReport(3, 'Dana')

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/reports/3/approve')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({ approved_by: 'Dana' })
    expect(result.status).toBe('approved')
  })

  it.each([
    [409, { errors: { status: 'This report is already approved.' } }, 'This report is already approved.'],
    [422, { errors: { approved_by: 'This field is required.' } }, 'This field is required.'],
    [404, { errors: { report: 'Report not found.' } }, 'Report not found.'],
  ])('shows the server message for HTTP %s', async (status, body, message) => {
    fetchMock.mockResolvedValue(reply(status, body))
    const error = await approveReport(3, 'Dana').catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.message).toBe(message)
  })

  it('has a general message for an unexpected failure', async () => {
    fetchMock.mockResolvedValue(reply(500, {}))
    await expect(approveReport(3, 'Dana')).rejects.toThrow(/Could not approve/)
  })
})

import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useReportDetail, useReports } from './hooks'
import { makeAnalysis, makeDetail, makeItem } from './test/fixtures'

const fetchMock = vi.fn()
const json = (status: number, body: unknown) => ({
  status,
  ok: status >= 200 && status < 300,
  json: async () => body,
})
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

function setHidden(hidden: boolean) {
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => hidden })
  document.dispatchEvent(new Event('visibilitychange'))
}

beforeEach(() => vi.stubGlobal('fetch', fetchMock))
afterEach(() => {
  fetchMock.mockReset()
  setHidden(false)
})

const detailCalls = () => fetchMock.mock.calls.filter(([u]) => /\/api\/reports\/\d+$/.test(u)).length

describe('useReportDetail', () => {
  it('drops the previous error when another report is selected', async () => {
    fetchMock.mockImplementation(async (url: string) =>
      url.endsWith('/1')
        ? json(404, { errors: { report: 'Report not found.' } })
        : new Promise(() => {}), // report 2 never answers
    )
    const { result, rerender } = renderHook(({ id }) => useReportDetail(id, 20), {
      initialProps: { id: 1 },
    })
    await waitFor(() => expect(result.current.error).toBe('Report not found.'))

    rerender({ id: 2 })
    expect(result.current.error).toBeNull()
    expect(result.current.detail).toBeNull()
  })

  it('does not let a late error of the old report show on the new one', async () => {
    let failOld: (v: unknown) => void = () => {}
    fetchMock.mockImplementation((url: string) =>
      url.endsWith('/1')
        ? new Promise((r) => (failOld = r))
        : Promise.resolve(json(200, makeDetail({ id: 2 }))),
    )
    const { result, rerender } = renderHook(({ id }) => useReportDetail(id, 1000), {
      initialProps: { id: 1 },
    })
    rerender({ id: 2 })
    await waitFor(() => expect(result.current.detail?.id).toBe(2))
    await act(async () => failOld(json(500, {})))
    expect(result.current.error).toBeNull()
    expect(result.current.detail?.id).toBe(2)
  })

  it('shows a new error for the new report if its own load fails', async () => {
    fetchMock.mockImplementation(async (url: string) =>
      json(404, { errors: { report: url.endsWith('/1') ? 'one' : 'two' } }),
    )
    const { result, rerender } = renderHook(({ id }) => useReportDetail(id, 1000), {
      initialProps: { id: 1 },
    })
    await waitFor(() => expect(result.current.error).toBe('one'))
    rerender({ id: 2 })
    await waitFor(() => expect(result.current.error).toBe('two'))
  })

  it('clears the error after a later poll succeeds', async () => {
    let ok = false
    fetchMock.mockImplementation(async () => (ok ? json(200, makeDetail()) : json(500, {})))
    const { result } = renderHook(() => useReportDetail(1, 20))
    await waitFor(() => expect(result.current.error).not.toBeNull())
    ok = true
    await waitFor(() => expect(result.current.error).toBeNull())
    expect(result.current.detail?.id).toBe(1)
  })

  it.each(['approved', 'failed'])('stops polling once the report is %s', async (status) => {
    fetchMock.mockImplementation(async () =>
      json(200, makeDetail({ analysis: makeAnalysis({ status }) })),
    )
    const { result } = renderHook(() => useReportDetail(1, 15))
    await waitFor(() => expect(result.current.detail).not.toBeNull())
    await sleep(30)
    const calls = detailCalls()
    await sleep(120)
    expect(detailCalls()).toBe(calls)
  })

  it.each(['processing', 'pending_approval'])('keeps polling while the report is %s', async (status) => {
    fetchMock.mockImplementation(async () =>
      json(200, makeDetail({ analysis: makeAnalysis({ status }) })),
    )
    renderHook(() => useReportDetail(1, 15))
    await waitFor(() => expect(detailCalls()).toBeGreaterThan(3))
  })

  it('fetches again on reload even after it stopped', async () => {
    fetchMock.mockImplementation(async () =>
      json(200, makeDetail({ analysis: makeAnalysis({ status: 'approved' }) })),
    )
    const { result } = renderHook(() => useReportDetail(1, 15))
    await waitFor(() => expect(result.current.detail).not.toBeNull())
    await sleep(40)
    const before = detailCalls()
    act(() => result.current.reload())
    await waitFor(() => expect(detailCalls()).toBeGreaterThan(before))
  })

  it('does not start a second request while one is still running', async () => {
    fetchMock.mockImplementation(() => new Promise(() => {}))
    renderHook(() => useReportDetail(1, 10))
    await sleep(100)
    expect(detailCalls()).toBe(1)
  })

  it('does not poll while the tab is hidden, and catches up when it is shown', async () => {
    fetchMock.mockImplementation(async () => json(200, makeDetail()))
    const { result } = renderHook(() => useReportDetail(1, 15))
    await waitFor(() => expect(result.current.detail).not.toBeNull())
    setHidden(true)
    await sleep(30)
    const calls = detailCalls()
    await sleep(100)
    expect(detailCalls()).toBe(calls)

    setHidden(false)
    await waitFor(() => expect(detailCalls()).toBeGreaterThan(calls))
  })

  it('fetches nothing without an id', async () => {
    renderHook(() => useReportDetail(null, 10))
    await sleep(50)
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

describe('useReports', () => {
  it('does not start a second request while one is still running', async () => {
    fetchMock.mockImplementation(() => new Promise(() => {}))
    renderHook(() => useReports(10))
    await sleep(100)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('does not poll while the tab is hidden, and catches up when it is shown', async () => {
    fetchMock.mockImplementation(async () => json(200, [makeItem()]))
    const { result } = renderHook(() => useReports(15))
    await waitFor(() => expect(result.current.reports).not.toBeNull())
    setHidden(true)
    await sleep(30)
    const calls = fetchMock.mock.calls.length
    await sleep(100)
    expect(fetchMock.mock.calls.length).toBe(calls)

    setHidden(false)
    await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThan(calls))
  })

  it('keeps polling after an error and recovers', async () => {
    let ok = false
    fetchMock.mockImplementation(async () => (ok ? json(200, [makeItem()]) : json(500, {})))
    const { result } = renderHook(() => useReports(15))
    await waitFor(() => expect(result.current.error).toMatch(/Could not load/))
    ok = true
    await waitFor(() => expect(result.current.error).toBeNull())
    expect(result.current.reports).toHaveLength(1)
  })
})

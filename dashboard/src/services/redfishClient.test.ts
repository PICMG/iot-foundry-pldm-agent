import { afterEach, describe, expect, it, vi } from 'vitest'
import { RedfishClient } from './redfishClient'

function jsonResponse(payload: unknown, init: ResponseInit = {}): Response {
  const headers = new Headers(init.headers)
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  return new Response(JSON.stringify(payload), {
    ...init,
    headers,
  })
}

describe('RedfishClient', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('builds collection URLs and includes auth token headers', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ Name: 'Systems' }))
    vi.stubGlobal('fetch', fetchMock)

    const client = new RedfishClient({
      baseUrl: 'http://127.0.0.1:8000/redfish/v1',
      getToken: () => 'token-123',
    })

    await client.getResource('/Systems')

    const [url, requestInit] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://127.0.0.1:8000/redfish/v1/Systems')

    const headers = new Headers(requestInit.headers)
    expect(headers.get('X-Auth-Token')).toBe('token-123')
    expect(headers.get('Accept')).toBe('application/json')
  })

  it('uses relative proxy base URLs to avoid cross-origin calls', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ Name: 'Systems' }))
    vi.stubGlobal('fetch', fetchMock)

    const client = new RedfishClient({
      baseUrl: '/redfish/v1',
    })

    await client.getResource('/Systems')

    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toBe('/redfish/v1/Systems')
  })

  it('creates a session and parses returned token and location headers', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(
        { Name: 'Session' },
        {
          status: 201,
          headers: {
            'X-Auth-Token': 'abc123',
            Location: '/redfish/v1/SessionService/Sessions/abc123',
          },
        },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    const client = new RedfishClient({ baseUrl: 'http://127.0.0.1:8000/redfish/v1' })
    const result = await client.createSession({ username: 'admin', password: 'password' })

    expect(result.token).toBe('abc123')
    expect(result.sessionUri).toBe('/redfish/v1/SessionService/Sessions/abc123')

    const [url, requestInit] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://127.0.0.1:8000/redfish/v1/SessionService/Sessions')
    expect(requestInit.method).toBe('POST')

    const body = JSON.parse(String(requestInit.body)) as { UserName: string; Password: string }
    expect(body.UserName).toBe('admin')
    expect(body.Password).toBe('password')
  })

  it('polls TaskService and expands member resources into summaries', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ Tasks: { '@odata.id': '/redfish/v1/TaskService/Tasks' } }))
      .mockResolvedValueOnce(
        jsonResponse({
          Members: [{ '@odata.id': '/redfish/v1/TaskService/Tasks/545' }],
          'Members@odata.count': 1,
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          Id: '545',
          Name: 'Task 545',
          TaskState: 'Completed',
          TaskStatus: 'OK',
          '@odata.id': '/redfish/v1/TaskService/Tasks/545',
          Messages: [{ Message: 'The task completed successfully.' }],
        }),
      )

    vi.stubGlobal('fetch', fetchMock)

    const client = new RedfishClient({ baseUrl: 'http://127.0.0.1:8000/redfish/v1' })
    const tasks = await client.pollTasks()

    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(tasks).toHaveLength(1)
    expect(tasks[0].id).toBe('545')
    expect(tasks[0].state).toBe('Completed')
    expect(tasks[0].status).toBe('OK')
    expect(tasks[0].messages).toEqual(['The task completed successfully.'])
  })
})

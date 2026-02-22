import type {
  CreateSessionResult,
  RedfishCollection,
  RedfishResource,
  TaskSummary,
} from '../types/redfish'
import { isCollection, isODataLink, normalizeRedfishPath, resourceDisplayName, toODataPath } from '../utils/redfish'

interface RedfishClientOptions {
  baseUrl: string
  getToken?: () => string | undefined
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  bodyJson?: unknown
  headers?: HeadersInit
  allowErrorStatus?: boolean
}

interface RequestResult<T> {
  status: number
  headers: Headers
  data: T | null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function joinPathParts(...parts: string[]): string {
  return parts
    .map((part, index) => {
      if (index === 0) {
        return part.replace(/^\/+/, '').replace(/\/+$/, '')
      }
      return part.replace(/^\/+/, '').replace(/\/+$/, '')
    })
    .filter((part) => part.length > 0)
    .join('/')
}

function isAbsoluteHttpUrl(value: string): boolean {
  return /^https?:\/\//i.test(value)
}

function looksLikeHost(value: string): boolean {
  const hostCandidate = value.split('/')[0]
  return hostCandidate === 'localhost' || hostCandidate.includes('.') || hostCandidate.includes(':')
}

function normalizeBaseUrl(baseUrl: string): string {
  const trimmed = baseUrl.trim()

  if (trimmed.length === 0) {
    return '/redfish/v1'
  }

  if (isAbsoluteHttpUrl(trimmed) || looksLikeHost(trimmed)) {
    const prefixed = isAbsoluteHttpUrl(trimmed) ? trimmed : `http://${trimmed}`
    const url = new URL(prefixed)
    const path = url.pathname === '/' ? '/redfish/v1' : url.pathname.replace(/\/+$/, '')
    url.pathname = path
    url.search = ''
    url.hash = ''
    return url.toString().replace(/\/+$/, '')
  }

  if (trimmed.startsWith('/')) {
    const path = trimmed === '/' ? '/redfish/v1' : trimmed.replace(/\/+$/, '')
    return path
  }

  return normalizeRedfishPath(trimmed)
}

export class RedfishRequestError extends Error {
  readonly status: number
  readonly body: unknown

  constructor(message: string, status: number, body: unknown) {
    super(message)
    this.name = 'RedfishRequestError'
    this.status = status
    this.body = body
  }
}

export class RedfishClient {
  private readonly baseUrl: string
  private readonly getToken?: () => string | undefined

  constructor(options: RedfishClientOptions) {
    this.baseUrl = normalizeBaseUrl(options.baseUrl)
    this.getToken = options.getToken
  }

  private buildUrl(path: string): string {
    if (isAbsoluteHttpUrl(path)) {
      return path
    }

    const normalizedPath = normalizeRedfishPath(path)

    if (isAbsoluteHttpUrl(this.baseUrl)) {
      const base = new URL(this.baseUrl)

      if (normalizedPath === '/redfish/v1') {
        return `${base.origin}/redfish/v1`
      }

      if (normalizedPath.startsWith('/redfish/')) {
        return `${base.origin}${normalizedPath}`
      }

      const joinedPath = joinPathParts(base.pathname, normalizedPath)
      return `${base.origin}/${joinedPath}`
    }

    if (normalizedPath === '/redfish/v1') {
      return this.baseUrl
    }

    if (normalizedPath.startsWith('/redfish/')) {
      return normalizedPath
    }

    const joinedPath = joinPathParts(this.baseUrl, normalizedPath)
    return `/${joinedPath}`
  }

  private async request<T>(path: string, options: RequestOptions = {}): Promise<RequestResult<T>> {
    const method = options.method ?? 'GET'
    const headers = new Headers(options.headers)

    if (!headers.has('Accept')) {
      headers.set('Accept', 'application/json')
    }

    if (options.bodyJson !== undefined && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }

    const token = this.getToken?.()
    if (token && !headers.has('X-Auth-Token')) {
      headers.set('X-Auth-Token', token)
    }

    const response = await fetch(this.buildUrl(path), {
      method,
      headers,
      body: options.bodyJson !== undefined ? JSON.stringify(options.bodyJson) : undefined,
    })

    const textPayload = response.status === 204 ? '' : await response.text()
    let data: unknown = null

    if (textPayload.length > 0) {
      const contentType = response.headers.get('content-type') ?? ''
      if (contentType.includes('json')) {
        try {
          data = JSON.parse(textPayload) as unknown
        } catch {
          data = { raw: textPayload }
        }
      } else {
        data = { raw: textPayload }
      }
    }

    if (!response.ok && !options.allowErrorStatus) {
      throw new RedfishRequestError(`Redfish request failed with status ${response.status}`, response.status, data)
    }

    return {
      status: response.status,
      headers: response.headers,
      data: data as T | null,
    }
  }

  async getServiceRoot(): Promise<RedfishResource> {
    return this.getResource('/redfish/v1')
  }

  async getResource<T extends RedfishResource = RedfishResource>(path: string): Promise<T> {
    const response = await this.request<T>(path)
    return (response.data ?? {}) as T
  }

  async patchResource(path: string, body: Record<string, unknown>): Promise<number> {
    const response = await this.request(path, {
      method: 'PATCH',
      bodyJson: body,
    })

    return response.status
  }

  async postAction(path: string, body: Record<string, unknown>): Promise<RequestResult<Record<string, unknown>>> {
    return this.request<Record<string, unknown>>(path, {
      method: 'POST',
      bodyJson: body,
    })
  }

  async deleteResource(path: string): Promise<number> {
    const response = await this.request(path, { method: 'DELETE', allowErrorStatus: true })
    return response.status
  }

  async createSession(credentials: { username: string; password: string }): Promise<CreateSessionResult> {
    const response = await this.request<Record<string, unknown>>('/SessionService/Sessions', {
      method: 'POST',
      bodyJson: {
        UserName: credentials.username,
        Password: credentials.password,
      },
      allowErrorStatus: true,
    })

    if (response.status >= 400) {
      throw new RedfishRequestError('Session creation failed', response.status, response.data)
    }

    return {
      token: response.headers.get('X-Auth-Token') ?? undefined,
      sessionUri: response.headers.get('Location') ?? undefined,
      status: response.status,
      payload: response.data,
    }
  }

  async runSimpleUpdate(payload: {
    ImageURI: string
    TransferProtocol?: string
    Username?: string
    Password?: string
  }): Promise<number> {
    const result = await this.postAction('/UpdateService/Actions/SimpleUpdate', payload)
    return result.status
  }

  async getCollectionMembers(path: string, limit?: number): Promise<RedfishResource[]> {
    const collection = await this.getResource<RedfishCollection>(path)
    if (!isCollection(collection)) {
      return []
    }

    const members = typeof limit === 'number' ? collection.Members.slice(0, limit) : collection.Members
    const resources = await Promise.all(
      members.map(async (member) => {
        try {
          return await this.getResource(member['@odata.id'])
        } catch {
          return null
        }
      }),
    )

    return resources.filter((item): item is RedfishResource => item !== null)
  }

  async pollTasks(): Promise<TaskSummary[]> {
    const taskService = await this.getResource('/TaskService')
    const tasksPath = toODataPath(taskService.Tasks)

    if (!tasksPath) {
      return []
    }

    const tasks = await this.getCollectionMembers(tasksPath)

    return tasks.map((task) => {
      const messages = Array.isArray(task.Messages)
        ? task.Messages.map((message) => {
            if (!isRecord(message)) {
              return ''
            }
            if (typeof message.Message === 'string') {
              return message.Message
            }
            if (typeof message.MessageId === 'string') {
              return message.MessageId
            }
            return ''
          }).filter((message) => message.length > 0)
        : []

      return {
        id: typeof task.Id === 'string' ? task.Id : resourceDisplayName(task),
        name: resourceDisplayName(task),
        state: typeof task.TaskState === 'string' ? task.TaskState : 'Unknown',
        status: typeof task.TaskStatus === 'string' ? task.TaskStatus : undefined,
        uri: typeof task['@odata.id'] === 'string' ? task['@odata.id'] : tasksPath,
        startTime: typeof task.StartTime === 'string' ? task.StartTime : undefined,
        endTime: typeof task.EndTime === 'string' ? task.EndTime : undefined,
        messages,
        raw: task,
      }
    })
  }

  async loadSystemAndChassisResources(): Promise<{
    root: RedfishResource
    systems: RedfishResource[]
    chassis: RedfishResource[]
  }> {
    const root = await this.getServiceRoot()
    const systemsPath = isODataLink(root.Systems) ? root.Systems['@odata.id'] : undefined
    const chassisPath = isODataLink(root.Chassis) ? root.Chassis['@odata.id'] : undefined

    const [systems, chassis] = await Promise.all([
      systemsPath ? this.getCollectionMembers(systemsPath) : Promise.resolve([]),
      chassisPath ? this.getCollectionMembers(chassisPath) : Promise.resolve([]),
    ])

    return { root, systems, chassis }
  }
}

export interface ODataLink {
  '@odata.id': string
}

export interface RedfishStatus {
  State?: string
  Health?: string
  HealthRollup?: string
}

export type RedfishResource = Record<string, unknown> & {
  '@odata.id'?: string
  '@odata.type'?: string
  Id?: string
  Name?: string
  Status?: RedfishStatus
}

export interface RedfishCollection extends RedfishResource {
  Members?: ODataLink[]
  'Members@odata.count'?: number
  'Members@odata.nextLink'?: string
}

export interface AuthSession {
  user: string
  token: string
  mode: 'server' | 'local'
  createdAt: string
  sessionUri?: string
}

export interface CreateSessionResult {
  token?: string
  sessionUri?: string
  status: number
  payload: Record<string, unknown> | null
}

export interface TaskSummary {
  id: string
  name: string
  state: string
  status?: string
  uri: string
  startTime?: string
  endTime?: string
  messages: string[]
  raw: RedfishResource
}

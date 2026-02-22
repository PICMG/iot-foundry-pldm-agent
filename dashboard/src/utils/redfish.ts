import type { ODataLink, RedfishResource, RedfishStatus } from '../types/redfish'

const REDFISH_ROOT = '/redfish/v1'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isPrimitive(value: unknown): value is string | number | boolean | null {
  return value === null || ['string', 'number', 'boolean'].includes(typeof value)
}

export function normalizeRedfishPath(target: string): string {
  const trimmed = target.trim()
  if (!trimmed) {
    return REDFISH_ROOT
  }

  let path = trimmed
  if (/^https?:\/\//i.test(trimmed)) {
    const parsed = new URL(trimmed)
    path = `${parsed.pathname}${parsed.search}${parsed.hash}`
  }

  if (!path.startsWith('/')) {
    path = `/${path}`
  }

  if (path === '/') {
    return REDFISH_ROOT
  }

  if (path.length > 1 && path.endsWith('/')) {
    path = path.slice(0, -1)
  }

  return path
}

export function isODataLink(value: unknown): value is ODataLink {
  return isRecord(value) && typeof value['@odata.id'] === 'string'
}

export function toODataPath(value: unknown): string | undefined {
  return isODataLink(value) ? value['@odata.id'] : undefined
}

export function isCollection(value: unknown): value is { Members: ODataLink[] } {
  return isRecord(value) && Array.isArray(value.Members)
}

export interface LinkedResource {
  key: string
  path: string
}

export interface ActionDescriptor {
  name: string
  target: string
}

export function extractLinkedResources(resource: RedfishResource): LinkedResource[] {
  const found = new Map<string, string>()

  Object.entries(resource).forEach(([key, value]) => {
    if (isODataLink(value)) {
      found.set(`${key}:0`, value['@odata.id'])
      return
    }

    if (Array.isArray(value)) {
      value.forEach((item, index) => {
        if (isODataLink(item)) {
          found.set(`${key}:${index}`, item['@odata.id'])
        }
      })
    }
  })

  return [...found.entries()].map(([key, path]) => ({ key, path }))
}

function collectActionTargets(node: Record<string, unknown>, prefix: string, output: ActionDescriptor[]): void {
  Object.entries(node).forEach(([key, value]) => {
    if (key === '@odata.type' || !isRecord(value)) {
      return
    }

    const nextName = prefix.length > 0 ? `${prefix}.${key}` : key
    const target = typeof value.target === 'string' ? value.target : undefined

    if (target) {
      output.push({ name: nextName, target })
      return
    }

    collectActionTargets(value, nextName, output)
  })
}

export function extractSupportedActions(resource: RedfishResource): ActionDescriptor[] {
  const actionsNode = resource.Actions
  if (!isRecord(actionsNode)) {
    return []
  }

  const collected: ActionDescriptor[] = []
  collectActionTargets(actionsNode, '', collected)

  return collected.sort((left, right) => left.name.localeCompare(right.name))
}

export function getStatusTone(status: RedfishStatus | undefined): 'ok' | 'warning' | 'critical' | 'unknown' {
  if (!status) {
    return 'unknown'
  }

  const health = (status.Health ?? '').toLowerCase()
  const state = (status.State ?? '').toLowerCase()

  if (health === 'ok') {
    if (state === 'disabled' || state === 'standbyoffline') {
      return 'warning'
    }
    return 'ok'
  }

  if (health.includes('warn')) {
    return 'warning'
  }

  if (health.includes('critical') || health.includes('error')) {
    return 'critical'
  }

  if (state.includes('disabled') || state.includes('off') || state.includes('standby')) {
    return 'warning'
  }

  return 'unknown'
}

export function resourceDisplayName(resource: RedfishResource): string {
  if (typeof resource.Name === 'string' && resource.Name.trim().length > 0) {
    return resource.Name
  }

  if (typeof resource.Id === 'string' && resource.Id.trim().length > 0) {
    return resource.Id
  }

  if (typeof resource['@odata.id'] === 'string') {
    const segments = resource['@odata.id'].split('/').filter(Boolean)
    return segments[segments.length - 1] ?? resource['@odata.id']
  }

  return 'Unnamed Resource'
}

export function pickPrimitiveFields(resource: RedfishResource, maxFields = 24): Array<[string, string]> {
  const rows: Array<[string, string]> = []

  Object.entries(resource).forEach(([key, value]) => {
    if (rows.length >= maxFields || key.startsWith('@')) {
      return
    }

    if (isPrimitive(value)) {
      rows.push([key, String(value)])
      return
    }

    if (Array.isArray(value) && value.every(isPrimitive)) {
      rows.push([key, value.map(String).join(', ')])
      return
    }

    if (key === 'Status' && isRecord(value)) {
      const state = typeof value.State === 'string' ? value.State : 'Unknown'
      const health = typeof value.Health === 'string' ? value.Health : 'Unknown'
      rows.push([key, `State: ${state} | Health: ${health}`])
    }
  })

  return rows
}

export function formatIsoDate(value: string | undefined): string {
  if (!value) {
    return 'N/A'
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return parsed.toLocaleString()
}

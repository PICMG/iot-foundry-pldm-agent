import { useCallback, useEffect, useMemo, useState } from 'react'
import JsonPanel from '../components/JsonPanel'
import ResourceTable from '../components/ResourceTable'
import StatusPill from '../components/StatusPill'
import SupportedActions from '../components/SupportedActions'
import { useClient } from '../state/ClientContext'
import type { RedfishResource } from '../types/redfish'
import {
  formatIsoDate,
  getStatusTone,
  isODataLink,
  resourceDisplayName,
  toODataPath,
} from '../utils/redfish'

interface AutomationNodeSummary {
  id: string
  name: string
  nodeType: string
  nodeState: string
  statusState: string
  health: string
  uri: string
  instrumentationPath?: string
  outputControlPath?: string
  positionSensorPath?: string
  chassisPath?: string
  actionsCount: number
  raw: RedfishResource
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function toNodeSummary(resource: RedfishResource): AutomationNodeSummary {
  const status = resource.Status
  const links = isRecord(resource.Links) ? resource.Links : undefined

  const chassisPath = Array.isArray(links?.Chassis)
    ? links.Chassis.find((item) => isODataLink(item))?.['@odata.id']
    : undefined

  const actionsNode = isRecord(resource.Actions) ? resource.Actions : undefined
  const actionsCount = actionsNode
    ? Object.keys(actionsNode).filter((key) => key !== '@odata.type' && key !== 'Oem').length
    : 0

  return {
    id: typeof resource.Id === 'string' ? resource.Id : resourceDisplayName(resource),
    name: resourceDisplayName(resource),
    nodeType: typeof resource.NodeType === 'string' ? resource.NodeType : 'Unknown',
    nodeState: typeof resource.NodeState === 'string' ? resource.NodeState : 'Unknown',
    statusState: typeof status?.State === 'string' ? status.State : 'Unknown',
    health: typeof status?.Health === 'string' ? status.Health : 'Unknown',
    uri: typeof resource['@odata.id'] === 'string' ? resource['@odata.id'] : '',
    instrumentationPath: toODataPath(resource.Instrumentation),
    outputControlPath: links ? toODataPath(links.OutputControl) : undefined,
    positionSensorPath: links ? toODataPath(links.PositionSensor) : undefined,
    chassisPath,
    actionsCount,
    raw: resource,
  }
}

function AutomationPage() {
  const { client } = useClient()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [root, setRoot] = useState<RedfishResource | null>(null)
  const [nodes, setNodes] = useState<AutomationNodeSummary[]>([])
  const [selectedNodeUri, setSelectedNodeUri] = useState<string>('')
  const [instrumentation, setInstrumentation] = useState<RedfishResource | null>(null)
  const [lastUpdated, setLastUpdated] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setError(null)

      const nextRoot = await client.getServiceRoot()
      const collectionPath = toODataPath(nextRoot.AutomationNodes)
      if (!collectionPath) {
        throw new Error('Service root did not provide an AutomationNodes collection link.')
      }

      const memberResources = await client.getCollectionMembers(collectionPath)
      const nextNodes = memberResources.map(toNodeSummary)

      setRoot(nextRoot)
      setNodes(nextNodes)
      setSelectedNodeUri((current) => {
        if (current.length > 0 && nextNodes.some((node) => node.uri === current)) {
          return current
        }
        return nextNodes[0]?.uri ?? ''
      })
      setLastUpdated(new Date().toISOString())
    } catch (refreshError) {
      const message = refreshError instanceof Error ? refreshError.message : 'Failed to load automation nodes.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [client])

  useEffect(() => {
    void refresh()

    const intervalId = window.setInterval(() => {
      void refresh()
    }, 5000)

    return () => window.clearInterval(intervalId)
  }, [refresh])

  const selectedNode = useMemo(
    () => nodes.find((node) => node.uri === selectedNodeUri) ?? null,
    [nodes, selectedNodeUri],
  )

  useEffect(() => {
    let active = true

    if (!selectedNode?.instrumentationPath) {
      setInstrumentation(null)
      return () => {
        active = false
      }
    }

    void client
      .getResource(selectedNode.instrumentationPath)
      .then((resource) => {
        if (active) {
          setInstrumentation(resource)
        }
      })
      .catch(() => {
        if (active) {
          setInstrumentation(null)
        }
      })

    return () => {
      active = false
    }
  }, [client, selectedNode?.instrumentationPath])

  return (
    <section>
      <header className="page-head">
        <h2 className="page-title">Automation View</h2>
        <p className="page-subtitle">
          Graphical status of all resources in <code>/redfish/v1/AutomationNodes</code>, including advertised actions.
        </p>
      </header>

      <div className="panel inline-meta">
        <p>Auto-refresh: every 5 seconds</p>
        <p>Last updated: {formatIsoDate(lastUpdated ?? undefined)}</p>
        <button className="button-secondary" type="button" onClick={() => void refresh()}>
          Refresh Now
        </button>
      </div>

      {loading ? <p className="loading">Loading automation nodes...</p> : null}
      {error ? <p className="error-banner">{error}</p> : null}

      <div className="panel">
        <h3>Automation Nodes</h3>
        {nodes.length === 0 ? <p className="muted">No automation nodes were discovered.</p> : null}
        <div className="card-grid">
          {nodes.map((node) => (
            <button
              key={node.uri}
              type="button"
              className={`resource-card selectable ${selectedNodeUri === node.uri ? 'selected' : ''}`}
              onClick={() => setSelectedNodeUri(node.uri)}
            >
              <div className="card-head">
                <h4>{node.name}</h4>
                <StatusPill tone={getStatusTone({ State: node.statusState, Health: node.health })} label={node.statusState} />
              </div>
              <p>Health: {node.health}</p>
              <p>NodeState: {node.nodeState}</p>
              <p>NodeType: {node.nodeType}</p>
              <p>Actions: {node.actionsCount}</p>
              <p className="resource-path">{node.uri}</p>
            </button>
          ))}
        </div>
      </div>

      {selectedNode ? (
        <div className="panel-grid two-column">
          <article className="panel">
            <h3>Selected Node Details</h3>
            <ResourceTable resource={selectedNode.raw} />
            <div className="list-stack top-space-sm">
              {selectedNode.chassisPath ? <p className="resource-path">Chassis: {selectedNode.chassisPath}</p> : null}
              {selectedNode.outputControlPath ? <p className="resource-path">OutputControl: {selectedNode.outputControlPath}</p> : null}
              {selectedNode.positionSensorPath ? <p className="resource-path">PositionSensor: {selectedNode.positionSensorPath}</p> : null}
              {selectedNode.instrumentationPath ? (
                <p className="resource-path">Instrumentation: {selectedNode.instrumentationPath}</p>
              ) : null}
            </div>
          </article>

          <SupportedActions resource={selectedNode.raw} title="Supported Actions (Read Only)" />

          {instrumentation ? (
            <article className="panel">
              <h3>Instrumentation Snapshot</h3>
              <ResourceTable resource={instrumentation} />
            </article>
          ) : null}

          <article className="panel">
            <JsonPanel title="Selected Node JSON" data={selectedNode.raw} />
          </article>
        </div>
      ) : null}

      {root ? (
        <article className="panel">
          <h3>Service Root Snapshot</h3>
          <ResourceTable resource={root} />
        </article>
      ) : null}
    </section>
  )
}

export default AutomationPage

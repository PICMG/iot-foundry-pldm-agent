import { useCallback, useEffect, useMemo, useState } from 'react'
import JsonPanel from '../components/JsonPanel'
import ResourceTable from '../components/ResourceTable'
import StatusPill from '../components/StatusPill'
import SupportedActions from '../components/SupportedActions'
import { useClient } from '../state/ClientContext'
import type { RedfishResource } from '../types/redfish'
import { formatIsoDate, getStatusTone, resourceDisplayName, toODataPath } from '../utils/redfish'

interface ChassisSummary {
  id: string
  name: string
  chassisType: string
  state: string
  health: string
  powerState: string
  uri: string
  sensorsPath?: string
  controlsPath?: string
  assemblyPath?: string
  actionsCount: number
  raw: RedfishResource
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function toChassisSummary(resource: RedfishResource): ChassisSummary {
  const status = resource.Status
  const actionsNode = isRecord(resource.Actions) ? resource.Actions : undefined
  const actionsCount = actionsNode
    ? Object.keys(actionsNode).filter((key) => key !== '@odata.type' && key !== 'Oem').length
    : 0

  return {
    id: typeof resource.Id === 'string' ? resource.Id : resourceDisplayName(resource),
    name: resourceDisplayName(resource),
    chassisType: typeof resource.ChassisType === 'string' ? resource.ChassisType : 'Unknown',
    state: typeof status?.State === 'string' ? status.State : 'Unknown',
    health: typeof status?.Health === 'string' ? status.Health : 'Unknown',
    powerState: typeof resource.PowerState === 'string' ? resource.PowerState : 'Unknown',
    uri: typeof resource['@odata.id'] === 'string' ? resource['@odata.id'] : '',
    sensorsPath: toODataPath(resource.Sensors),
    controlsPath: toODataPath(resource.Controls),
    assemblyPath: toODataPath(resource.Assembly),
    actionsCount,
    raw: resource,
  }
}

function ChassisPage() {
  const { client } = useClient()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [root, setRoot] = useState<RedfishResource | null>(null)
  const [chassis, setChassis] = useState<ChassisSummary[]>([])
  const [selectedChassisUri, setSelectedChassisUri] = useState<string>('')
  const [lastUpdated, setLastUpdated] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setError(null)

      const nextRoot = await client.getServiceRoot()
      const collectionPath = toODataPath(nextRoot.Chassis)
      if (!collectionPath) {
        throw new Error('Service root did not provide a Chassis collection link.')
      }

      const memberResources = await client.getCollectionMembers(collectionPath)
      const nextChassis = memberResources.map(toChassisSummary)

      setRoot(nextRoot)
      setChassis(nextChassis)
      setSelectedChassisUri((current) => {
        if (current.length > 0 && nextChassis.some((item) => item.uri === current)) {
          return current
        }
        return nextChassis[0]?.uri ?? ''
      })
      setLastUpdated(new Date().toISOString())
    } catch (refreshError) {
      const message = refreshError instanceof Error ? refreshError.message : 'Failed to load chassis data.'
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

  const selectedChassis = useMemo(
    () => chassis.find((item) => item.uri === selectedChassisUri) ?? null,
    [chassis, selectedChassisUri],
  )

  return (
    <section>
      <header className="page-head">
        <h2 className="page-title">Chassis View</h2>
        <p className="page-subtitle">
          Graphical status of all resources in <code>/redfish/v1/Chassis</code>, with read-only action visibility.
        </p>
      </header>

      <div className="panel inline-meta">
        <p>Auto-refresh: every 5 seconds</p>
        <p>Last updated: {formatIsoDate(lastUpdated ?? undefined)}</p>
        <button className="button-secondary" type="button" onClick={() => void refresh()}>
          Refresh Now
        </button>
      </div>

      {loading ? <p className="loading">Loading chassis resources...</p> : null}
      {error ? <p className="error-banner">{error}</p> : null}

      <div className="panel">
        <h3>Chassis Collection</h3>
        {chassis.length === 0 ? <p className="muted">No chassis members were discovered.</p> : null}
        <div className="card-grid">
          {chassis.map((item) => (
            <button
              key={item.uri}
              type="button"
              className={`resource-card selectable ${selectedChassisUri === item.uri ? 'selected' : ''}`}
              onClick={() => setSelectedChassisUri(item.uri)}
            >
              <div className="card-head">
                <h4>{item.name}</h4>
                <StatusPill tone={getStatusTone({ State: item.state, Health: item.health })} label={item.state} />
              </div>
              <p>Health: {item.health}</p>
              <p>Type: {item.chassisType}</p>
              <p>Power: {item.powerState}</p>
              <p>Actions: {item.actionsCount}</p>
              <p className="resource-path">{item.uri}</p>
            </button>
          ))}
        </div>
      </div>

      {selectedChassis ? (
        <div className="panel-grid two-column">
          <article className="panel">
            <h3>Selected Chassis Details</h3>
            <ResourceTable resource={selectedChassis.raw} />
            <div className="list-stack top-space-sm">
              {selectedChassis.sensorsPath ? <p className="resource-path">Sensors: {selectedChassis.sensorsPath}</p> : null}
              {selectedChassis.controlsPath ? <p className="resource-path">Controls: {selectedChassis.controlsPath}</p> : null}
              {selectedChassis.assemblyPath ? <p className="resource-path">Assembly: {selectedChassis.assemblyPath}</p> : null}
            </div>
          </article>

          <SupportedActions resource={selectedChassis.raw} title="Supported Actions (Read Only)" />

          <article className="panel two-column-span">
            <JsonPanel title="Selected Chassis JSON" data={selectedChassis.raw} />
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

export default ChassisPage

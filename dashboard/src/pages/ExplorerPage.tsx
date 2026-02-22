import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import JsonPanel from '../components/JsonPanel'
import ResourceTable from '../components/ResourceTable'
import { useClient } from '../state/ClientContext'
import type { RedfishResource } from '../types/redfish'
import {
  extractLinkedResources,
  isCollection,
  normalizeRedfishPath,
  resourceDisplayName,
} from '../utils/redfish'

function ExplorerPage() {
  const { client } = useClient()
  const [searchParams, setSearchParams] = useSearchParams()

  const currentPath = searchParams.get('path') ?? '/redfish/v1'
  const [pathInput, setPathInput] = useState(currentPath)

  const [resource, setResource] = useState<RedfishResource | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setPathInput(currentPath)
  }, [currentPath])

  const loadResource = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const payload = await client.getResource(currentPath)
      setResource(payload)
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : 'Unable to fetch resource.'
      setResource(null)
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }, [client, currentPath])

  useEffect(() => {
    void loadResource()
  }, [loadResource])

  const memberLinks = useMemo(() => {
    if (!resource || !isCollection(resource)) {
      return []
    }
    return resource.Members
  }, [resource])

  const relatedLinks = useMemo(() => {
    if (!resource) {
      return []
    }

    const memberSet = new Set(memberLinks.map((member) => member['@odata.id']))
    return extractLinkedResources(resource).filter(
      (item) => !memberSet.has(item.path) && item.path !== currentPath && item.path !== '/redfish/v1',
    )
  }, [resource, memberLinks, currentPath])

  const navigateTo = (nextPath: string) => {
    setSearchParams({ path: normalizeRedfishPath(nextPath) })
  }

  const handlePathSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    navigateTo(pathInput)
  }

  return (
    <section>
      <header className="page-head">
        <h2 className="page-title">Dynamic Resource Explorer</h2>
        <p className="page-subtitle">Browse collections and linked resources without hard-coded member IDs.</p>
      </header>

      <article className="panel">
        <form className="endpoint-form" onSubmit={handlePathSubmit}>
          <label className="field-label" htmlFor="resource-path">
            Resource Path
          </label>
          <input
            id="resource-path"
            className="endpoint-input"
            value={pathInput}
            onChange={(event) => setPathInput(event.target.value)}
            placeholder="/redfish/v1/Systems"
          />
          <button className="endpoint-button" type="submit">
            Open
          </button>
        </form>
      </article>

      {isLoading ? <p className="loading">Loading resource...</p> : null}
      {error ? <p className="error-banner">{error}</p> : null}

      {resource ? (
        <div className="panel-grid two-column">
          <article className="panel">
            <h3>{resourceDisplayName(resource)}</h3>
            <p className="resource-path">{typeof resource['@odata.id'] === 'string' ? resource['@odata.id'] : currentPath}</p>
            <ResourceTable resource={resource} />
          </article>

          <article className="panel">
            <h3>Collection Members</h3>
            {memberLinks.length === 0 ? <p className="muted">This resource is not a collection.</p> : null}
            <div className="list-stack">
              {memberLinks.map((member) => (
                <button
                  key={member['@odata.id']}
                  className="link-button"
                  type="button"
                  onClick={() => navigateTo(member['@odata.id'])}
                >
                  {member['@odata.id']}
                </button>
              ))}
            </div>

            <h3>Related Links</h3>
            {relatedLinks.length === 0 ? <p className="muted">No additional related links discovered.</p> : null}
            <div className="list-stack">
              {relatedLinks.map((item) => (
                <button
                  key={`${item.key}-${item.path}`}
                  className="link-button"
                  type="button"
                  onClick={() => navigateTo(item.path)}
                >
                  {item.key}
                  {' -> '}
                  {item.path}
                </button>
              ))}
            </div>
          </article>

          <article className="panel two-column-span">
            <JsonPanel title="Resource JSON" data={resource} />
          </article>
        </div>
      ) : null}
    </section>
  )
}

export default ExplorerPage

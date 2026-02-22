import type { RedfishResource } from '../types/redfish'
import { extractSupportedActions } from '../utils/redfish'

interface SupportedActionsProps {
  resource: RedfishResource
  title?: string
}

function SupportedActions({ resource, title = 'Supported Actions' }: SupportedActionsProps) {
  const actions = extractSupportedActions(resource)

  return (
    <article className="panel">
      <h3>{title}</h3>
      {actions.length === 0 ? <p className="muted">No actions advertised by this resource.</p> : null}
      <ul className="action-list">
        {actions.map((action) => (
          <li className="action-item" key={`${action.name}-${action.target}`}>
            <p className="action-name">{action.name}</p>
            <p className="resource-path">{action.target}</p>
          </li>
        ))}
      </ul>
    </article>
  )
}

export default SupportedActions

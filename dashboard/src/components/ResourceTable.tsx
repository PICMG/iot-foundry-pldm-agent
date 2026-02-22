import type { RedfishResource } from '../types/redfish'
import { pickPrimitiveFields } from '../utils/redfish'

interface ResourceTableProps {
  resource: RedfishResource
  emptyLabel?: string
}

function ResourceTable({ resource, emptyLabel = 'No primitive properties to display.' }: ResourceTableProps) {
  const rows = pickPrimitiveFields(resource)

  if (rows.length === 0) {
    return <p className="muted">{emptyLabel}</p>
  }

  return (
    <div className="table-wrap">
      <table className="resource-table">
        <tbody>
          {rows.map(([key, value]) => (
            <tr key={key}>
              <th scope="row">{key}</th>
              <td>{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default ResourceTable

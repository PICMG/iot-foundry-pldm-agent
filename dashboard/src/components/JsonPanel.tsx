interface JsonPanelProps {
  title?: string
  data: unknown
  defaultOpen?: boolean
}

function JsonPanel({ title = 'Raw JSON', data, defaultOpen = false }: JsonPanelProps) {
  return (
    <details className="raw-json" open={defaultOpen}>
      <summary>{title}</summary>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </details>
  )
}

export default JsonPanel

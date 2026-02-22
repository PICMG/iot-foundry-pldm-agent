interface StatusPillProps {
  tone: 'ok' | 'warning' | 'critical' | 'unknown'
  label: string
}

function StatusPill({ tone, label }: StatusPillProps) {
  return <span className={`status-pill tone-${tone}`}>{label}</span>
}

export default StatusPill

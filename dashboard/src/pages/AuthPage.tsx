import { type FormEvent, useState } from 'react'
import { useClient } from '../state/ClientContext'
import { formatIsoDate } from '../utils/redfish'

function AuthPage() {
  const { login, session } = useClient()
  const [username, setUsername] = useState('operator')
  const [password, setPassword] = useState('redfish')
  const [feedback, setFeedback] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setIsSubmitting(true)

    try {
      const result = await login(username.trim(), password)
      setFeedback(result.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section>
      <header className="page-head">
        <h2 className="page-title">Authentication Workflow</h2>
        <p className="page-subtitle">Authenticate to unlock the protected dashboard workflows.</p>
      </header>

      <div className="panel-grid two-column">
        <article className="panel">
          <h3>Login</h3>
          <form className="form-grid" onSubmit={handleSubmit}>
            <label className="field">
              <span className="field-label">Username</span>
              <input
                className="field-input"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
              />
            </label>

            <label className="field">
              <span className="field-label">Password</span>
              <input
                className="field-input"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>

            <button className="button-primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Authenticating...' : 'Authenticate'}
            </button>
          </form>

          {feedback ? <p className="success-banner">{feedback}</p> : null}
        </article>

        <article className="panel">
          <h3>Session State</h3>
          {!session ? <p className="muted">No active session in UI state.</p> : null}

          {session ? (
            <dl className="stats-grid">
              <div>
                <dt>User</dt>
                <dd>{session.user}</dd>
              </div>
              <div>
                <dt>Mode</dt>
                <dd>{session.mode}</dd>
              </div>
              <div>
                <dt>Created</dt>
                <dd>{formatIsoDate(session.createdAt)}</dd>
              </div>
              <div>
                <dt>Session URI</dt>
                <dd>{session.sessionUri ?? 'N/A'}</dd>
              </div>
              <div>
                <dt>Token Prefix</dt>
                <dd>{session.token.slice(0, 8)}</dd>
              </div>
            </dl>
          ) : null}
        </article>
      </div>
    </section>
  )
}

export default AuthPage

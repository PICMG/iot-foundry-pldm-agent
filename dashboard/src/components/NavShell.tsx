import { type FormEvent, useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useClient } from '../state/ClientContext'

function NavShell() {
  const { baseUrl, setBaseUrl, session, logout, isAuthenticated } = useClient()
  const [draftBaseUrl, setDraftBaseUrl] = useState(baseUrl)

  useEffect(() => {
    setDraftBaseUrl(baseUrl)
  }, [baseUrl])

  const handleEndpointSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setBaseUrl(draftBaseUrl)
  }

  return (
    <div className="app-shell">
      <header className="top-bar">
        <div className="top-row">
          <div className="brand-block">
            <h1 className="brand-title">Redfish Operations Console</h1>
            <p className="brand-subtitle">Dynamic Redfish workflow dashboard</p>
          </div>
          <div className="session-block">
            <span className="session-chip">
              {session ? `Session: ${session.user} (${session.mode})` : 'Session: not authenticated'}
            </span>
            {session ? (
              <button className="button-secondary" type="button" onClick={() => void logout()}>
                Logout
              </button>
            ) : null}
          </div>
        </div>

        <div className="nav-row">
          <nav className="main-nav" aria-label="Main">
            <NavLink to="/auth" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
              Authentication
            </NavLink>
            {isAuthenticated ? (
              <>
                <NavLink to="/chassis" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
                  Chassis View
                </NavLink>
                <NavLink to="/automation" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
                  Automation View
                </NavLink>
                <NavLink to="/jobs" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
                  Run Job
                </NavLink>
                <NavLink
                  to="/explorer?path=/redfish/v1/JobService"
                  className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
                >
                  JobService
                </NavLink>
                <NavLink to="/explorer" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
                  Explorer
                </NavLink>
              </>
            ) : (
              <>
                <span className="nav-link disabled">Chassis View</span>
                <span className="nav-link disabled">Automation View</span>
                <span className="nav-link disabled">Run Job</span>
                <span className="nav-link disabled">JobService</span>
                <span className="nav-link disabled">Explorer</span>
              </>
            )}
          </nav>

          <form className="endpoint-form" onSubmit={handleEndpointSubmit}>
            <label htmlFor="base-url" className="field-label">
              Base URL
            </label>
            <input
              id="base-url"
              className="endpoint-input"
              value={draftBaseUrl}
              onChange={(event) => setDraftBaseUrl(event.target.value)}
              placeholder="/redfish/v1"
            />
            <button className="endpoint-button" type="submit">
              Apply
            </button>
          </form>
        </div>
      </header>

      <main className="content-area">
        <Outlet />
      </main>
    </div>
  )
}

export default NavShell

import type { ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './App.css'
import NavShell from './components/NavShell'
import AutomationPage from './pages/AutomationPage'
import AuthPage from './pages/AuthPage'
import ChassisPage from './pages/ChassisPage'
import ExplorerPage from './pages/ExplorerPage'
import JobsPage from './pages/JobsPage'
import { ClientProvider, useClient } from './state/ClientContext'

function NotFoundPage() {
  return (
    <section className="panel">
      <h2 className="page-title">Route Not Found</h2>
      <p className="muted">Use the navigation menu to open a dashboard workflow.</p>
    </section>
  )
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useClient()

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />
  }

  return <>{children}</>
}

function HomeRedirect() {
  const { isAuthenticated } = useClient()
  return <Navigate to={isAuthenticated ? '/chassis' : '/auth'} replace />
}

function GuardedNotFoundPage() {
  const { isAuthenticated } = useClient()

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />
  }

  return <NotFoundPage />
}

function App() {
  return (
    <ClientProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<NavShell />}>
            <Route index element={<HomeRedirect />} />
            <Route path="/auth" element={<AuthPage />} />
            <Route
              path="/chassis"
              element={
                <RequireAuth>
                  <ChassisPage />
                </RequireAuth>
              }
            />
            <Route
              path="/automation"
              element={
                <RequireAuth>
                  <AutomationPage />
                </RequireAuth>
              }
            />
            <Route
              path="/jobs"
              element={
                <RequireAuth>
                  <JobsPage />
                </RequireAuth>
              }
            />
            <Route
              path="/explorer"
              element={
                <RequireAuth>
                  <ExplorerPage />
                </RequireAuth>
              }
            />
            <Route path="*" element={<GuardedNotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ClientProvider>
  )
}

export default App

/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { DEFAULT_REDFISH_BASE } from '../config'
import { RedfishClient } from '../services/redfishClient'
import type { AuthSession } from '../types/redfish'

interface LoginResult {
  mode: 'server' | 'local'
  message: string
}

interface ClientContextValue {
  baseUrl: string
  setBaseUrl: (nextUrl: string) => void
  session: AuthSession | null
  isAuthenticated: boolean
  client: RedfishClient
  login: (username: string, password: string) => Promise<LoginResult>
  logout: () => Promise<void>
}

const SESSION_STORAGE_KEY = 'redfish-dashboard-session'
const BASE_URL_STORAGE_KEY = 'redfish-dashboard-base-url'
const LEGACY_DIRECT_BASES = new Set([
  'http://127.0.0.1:8000/redfish/v1',
  'http://localhost:8000/redfish/v1',
])

function isLegacyDirectBase(value: string): boolean {
  if (LEGACY_DIRECT_BASES.has(value)) {
    return true
  }

  try {
    const parsed = new URL(value)
    const normalizedPath = parsed.pathname.replace(/\/+$/, '')

    return (
      (parsed.hostname === '127.0.0.1' || parsed.hostname === 'localhost') &&
      parsed.port === '8000' &&
      normalizedPath === '/redfish/v1'
    )
  } catch {
    return false
  }
}

const ClientContext = createContext<ClientContextValue | undefined>(undefined)

function readStoredBaseUrl(): string {
  if (typeof window === 'undefined') {
    return DEFAULT_REDFISH_BASE
  }

  const stored = window.localStorage.getItem(BASE_URL_STORAGE_KEY)
  if (!stored || stored.trim().length === 0) {
    return DEFAULT_REDFISH_BASE
  }

  const normalizedStored = stored.trim()
  if (isLegacyDirectBase(normalizedStored)) {
    return '/redfish/v1'
  }

  return stored
}

function readStoredSession(): AuthSession | null {
  if (typeof window === 'undefined') {
    return null
  }

  const stored = window.localStorage.getItem(SESSION_STORAGE_KEY)
  if (!stored) {
    return null
  }

  try {
    const parsed = JSON.parse(stored) as AuthSession
    if (typeof parsed.token !== 'string' || typeof parsed.user !== 'string') {
      return null
    }
    return parsed
  } catch {
    return null
  }
}

function makeLocalToken(): string {
  return `demo-${Math.random().toString(36).slice(2, 12)}`
}

export function ClientProvider({ children }: { children: React.ReactNode }) {
  const [baseUrl, setBaseUrlState] = useState(readStoredBaseUrl)
  const [session, setSession] = useState<AuthSession | null>(readStoredSession)

  const client = useMemo(
    () =>
      new RedfishClient({
        baseUrl,
        getToken: () => session?.token,
      }),
    [baseUrl, session?.token],
  )

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }
    window.localStorage.setItem(BASE_URL_STORAGE_KEY, baseUrl)
  }, [baseUrl])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    if (!session) {
      window.localStorage.removeItem(SESSION_STORAGE_KEY)
      return
    }

    window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session))
  }, [session])

  const setBaseUrl = useCallback((nextUrl: string) => {
    const trimmed = nextUrl.trim()
    if (trimmed.length > 0) {
      setBaseUrlState(trimmed)
    }
  }, [])

  const login = useCallback(
    async (username: string, password: string): Promise<LoginResult> => {
      try {
        const result = await client.createSession({ username, password })
        const token = result.token ?? makeLocalToken()
        const mode: 'server' | 'local' = result.token ? 'server' : 'local'

        setSession({
          user: username,
          token,
          mode,
          createdAt: new Date().toISOString(),
          sessionUri: result.sessionUri,
        })

        if (mode === 'server') {
          return { mode, message: `Authenticated through SessionService (HTTP ${result.status}).` }
        }

        return {
          mode,
          message: 'SessionService accepted the request but no token was returned; using local demo auth token.',
        }
      } catch {
        setSession({
          user: username,
          token: makeLocalToken(),
          mode: 'local',
          createdAt: new Date().toISOString(),
        })

        return {
          mode: 'local',
          message: 'SessionService request failed; switched to local demo auth mode for the workflow.',
        }
      }
    },
    [client],
  )

  const logout = useCallback(async () => {
    const currentSession = session

    if (currentSession?.mode === 'server' && currentSession.sessionUri) {
      try {
        await client.deleteResource(currentSession.sessionUri)
      } catch {
        // Session deletion can fail on static mockups; clear local state regardless.
      }
    }

    setSession(null)
  }, [client, session])

  const value = useMemo<ClientContextValue>(
    () => ({
      baseUrl,
      setBaseUrl,
      session,
      isAuthenticated: session !== null,
      client,
      login,
      logout,
    }),
    [baseUrl, setBaseUrl, session, client, login, logout],
  )

  return <ClientContext.Provider value={value}>{children}</ClientContext.Provider>
}

export function useClient(): ClientContextValue {
  const value = useContext(ClientContext)
  if (!value) {
    throw new Error('useClient must be used inside ClientProvider')
  }
  return value
}

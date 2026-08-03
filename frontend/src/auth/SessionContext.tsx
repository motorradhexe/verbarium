import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

import { ApiError, api } from '../api/client'
import type { Role, UserProfile } from '../api/types'
import { canActAs } from '../api/types'

interface SessionValue {
  user: UserProfile | null
  /** Null until the first `/auth/me` has answered. */
  loading: boolean
  /** Null while unknown, true when the instance has no accounts yet. */
  needsSetup: boolean | null
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  refresh: () => Promise<void>
  can: (role: Role) => boolean
}

const SessionContext = createContext<SessionValue | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [needsSetup, setNeedsSetup] = useState<boolean | null>(null)

  const refresh = useCallback(async () => {
    try {
      setUser(await api.me())
      setNeedsSetup(false)
    } catch (error) {
      if (error instanceof ApiError && error.isUnauthenticated) {
        setUser(null)
        // Only worth asking when nobody is signed in: an instance with a
        // session is by definition already set up.
        try {
          setNeedsSetup((await api.setupStatus()).completed === false)
        } catch {
          setNeedsSetup(null)
        }
      } else {
        setUser(null)
        setNeedsSetup(null)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const signIn = useCallback(async (email: string, password: string) => {
    setUser(await api.login(email, password))
    setNeedsSetup(false)
  }, [])

  const signOut = useCallback(async () => {
    await api.logout()
    setUser(null)
  }, [])

  const can = useCallback(
    (role: Role) => (user ? canActAs(user.role, role) : false),
    [user],
  )

  const value = useMemo(
    () => ({ user, loading, needsSetup, signIn, signOut, refresh, can }),
    [user, loading, needsSetup, signIn, signOut, refresh, can],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext)
  if (value === null) throw new Error('useSession must be used inside a SessionProvider')
  return value
}

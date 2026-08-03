import { BrowserRouter, Navigate, Route, Routes } from 'react-router'

import { SessionProvider, useSession } from './auth/SessionContext'
import { Layout } from './components/Layout'
import { Loading } from './components/Feedback'
import { LocaleProvider } from './i18n'
import { ConceptDetail } from './pages/ConceptDetail'
import { Login } from './pages/Login'
import { NewConcept } from './pages/NewConcept'
import { Setup } from './pages/Setup'
import { TermList } from './pages/TermList'

/** Decides what the app shows before any route matches.
 *
 *  Three states, in order: still asking the backend, an instance with no
 *  accounts at all, and nobody signed in. Only past those does the router
 *  take over.
 */
function Gate() {
  const { user, loading, needsSetup } = useSession()

  if (loading) {
    return (
      <Layout>
        <Loading />
      </Layout>
    )
  }

  if (needsSetup) return <Layout><Setup /></Layout>
  if (!user) return <Layout><Login /></Layout>

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<TermList />} />
        <Route path="concepts/new" element={<NewConcept />} />
        <Route path="concepts/:id" element={<ConceptDetail />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <LocaleProvider>
      <BrowserRouter>
        <SessionProvider>
          <Gate />
        </SessionProvider>
      </BrowserRouter>
    </LocaleProvider>
  )
}

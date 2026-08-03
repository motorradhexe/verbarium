import { useState, type FormEvent } from 'react'

import { ErrorMessage } from '../components/Feedback'
import { useSession } from '../auth/SessionContext'
import { useI18n } from '../i18n'

export function Login() {
  const { t } = useI18n()
  const { signIn } = useSession()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await signIn(email, password)
    } catch (failure) {
      setError(failure)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="narrow">
      <h1>{t.login.title}</h1>

      <form onSubmit={submit} className="stack">
        <label>
          {t.login.email}
          <input
            type="email"
            value={email}
            autoComplete="username"
            required
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>

        <label>
          {t.login.password}
          <input
            type="password"
            value={password}
            autoComplete="current-password"
            required
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>

        <ErrorMessage error={error} />

        <button type="submit" className="button" disabled={busy}>
          {t.login.submit}
        </button>
      </form>
    </div>
  )
}

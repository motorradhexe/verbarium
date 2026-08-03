import { useState, type FormEvent } from 'react'

import { api } from '../api/client'
import { ErrorMessage } from '../components/Feedback'
import { useSession } from '../auth/SessionContext'
import { useI18n } from '../i18n'

interface LanguageRow {
  code: string
  name: string
}

export function Setup() {
  const { t } = useI18n()
  const { refresh } = useSession()
  const [workspaceName, setWorkspaceName] = useState('')
  const [languages, setLanguages] = useState<LanguageRow[]>([
    { code: 'de', name: '' },
    { code: 'en', name: '' },
  ])
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)

  function updateLanguage(index: number, patch: Partial<LanguageRow>) {
    setLanguages((rows) => rows.map((row, at) => (at === index ? { ...row, ...patch } : row)))
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await api.runSetup({
        workspace_name: workspaceName,
        languages: languages
          .filter((row) => row.code.trim())
          .map((row) => ({ code: row.code.trim(), name: row.name.trim() || null })),
        admin_email: email,
        admin_display_name: displayName,
        admin_password: password,
      })
      // Setup does not sign anyone in; refreshing flips the app to the login
      // page now that an account exists.
      await refresh()
    } catch (failure) {
      setError(failure)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="narrow">
      <h1>{t.setup.title}</h1>
      <p className="muted">{t.setup.intro}</p>

      <form onSubmit={submit} className="stack">
        <label>
          {t.setup.workspaceName}
          <input
            value={workspaceName}
            required
            onChange={(event) => setWorkspaceName(event.target.value)}
          />
        </label>

        <fieldset>
          <legend>{t.setup.contentLanguages}</legend>
          <p className="muted small">{t.setup.contentLanguagesHint}</p>

          {languages.map((row, index) => (
            <div className="row" key={index}>
              <input
                aria-label={`${t.setup.contentLanguages} ${index + 1}`}
                value={row.code}
                placeholder="de"
                maxLength={2}
                className="input--code"
                onChange={(event) => updateLanguage(index, { code: event.target.value })}
              />
              <input
                aria-label={`${t.setup.contentLanguages} ${index + 1} — ${t.common.optional}`}
                value={row.name}
                placeholder={t.common.optional}
                onChange={(event) => updateLanguage(index, { name: event.target.value })}
              />
              {languages.length > 1 && (
                <button
                  type="button"
                  className="button button--quiet"
                  onClick={() => setLanguages((rows) => rows.filter((_, at) => at !== index))}
                >
                  ×
                </button>
              )}
            </div>
          ))}

          <button
            type="button"
            className="button button--quiet"
            onClick={() => setLanguages((rows) => [...rows, { code: '', name: '' }])}
          >
            {t.setup.addLanguage}
          </button>
        </fieldset>

        <fieldset>
          <legend>{t.setup.adminAccount}</legend>

          <label>
            {t.setup.displayName}
            <input
              value={displayName}
              required
              onChange={(event) => setDisplayName(event.target.value)}
            />
          </label>

          <label>
            {t.setup.email}
            <input
              type="email"
              value={email}
              autoComplete="username"
              required
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>

          <label>
            {t.setup.password}
            <input
              type="password"
              value={password}
              autoComplete="new-password"
              minLength={12}
              required
              onChange={(event) => setPassword(event.target.value)}
            />
            <span className="muted small">{t.setup.passwordHint}</span>
          </label>
        </fieldset>

        <ErrorMessage error={error} />

        <button type="submit" className="button" disabled={busy}>
          {t.setup.submit}
        </button>
      </form>
    </div>
  )
}

import { useState, type FormEvent } from 'react'

import { ApiError, api } from '../api/client'
import type { TermEntry } from '../api/types'
import { useSession } from '../auth/SessionContext'
import { ErrorMessage } from '../components/Feedback'
import { useI18n } from '../i18n'

/** Comma-separated input to a list, and back.
 *
 *  Exported for the tests: the round trip is where whitespace and stray
 *  separators cause empty entries to creep into synonyms.
 */
export function parseList(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

export function formatList(items: string[]): string {
  return items.join(', ')
}

interface Props {
  /** Given when editing an existing entry. */
  entry?: TermEntry
  /** Given when adding a language to a concept. */
  conceptId?: string
  onCancel: () => void
  onSaved: () => void
}

export function EntryEditor({ entry, conceptId, onCancel, onSaved }: Props) {
  const { t } = useI18n()
  const { can } = useSession()
  const [languageCode, setLanguageCode] = useState(entry?.language_code ?? '')
  const [term, setTerm] = useState(entry?.term ?? '')
  const [definition, setDefinition] = useState(entry?.definition ?? '')
  const [synonyms, setSynonyms] = useState(formatList(entry?.synonyms ?? []))
  const [nogo, setNogo] = useState(formatList(entry?.nogo_alternatives ?? []))
  const [contextExample, setContextExample] = useState(entry?.context_example ?? '')
  const [source, setSource] = useState(entry?.source ?? '')
  const [notes, setNotes] = useState(entry?.notes ?? '')
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setBusy(true)

    const fields = {
      term,
      definition: definition || null,
      synonyms: parseList(synonyms),
      nogo_alternatives: parseList(nogo),
      context_example: contextExample || null,
      source: source || null,
      // Only send notes when the role may see them — otherwise a viewer's
      // blanked null would wipe what an editor wrote. → D18
      ...(can('editor') ? { notes: notes || null } : {}),
    }

    try {
      if (entry) {
        // The version travels along so a stale edit is refused. → D4
        await api.updateTerm(entry.id, entry.version, fields)
      } else if (conceptId) {
        await api.addTerm(conceptId, { language_code: languageCode.trim().toLowerCase(), ...fields })
      }
      onSaved()
    } catch (failure) {
      setError(failure)
    } finally {
      setBusy(false)
    }
  }

  const conflict = error instanceof ApiError && error.isConflict

  return (
    <form className="panel stack" onSubmit={submit}>
      {!entry && (
        <label>
          {t.common.language}
          <input
            value={languageCode}
            placeholder="de"
            maxLength={2}
            required
            className="input--code"
            onChange={(event) => setLanguageCode(event.target.value)}
          />
        </label>
      )}

      <label>
        {t.entry.term}
        <input value={term} required onChange={(event) => setTerm(event.target.value)} />
      </label>

      <label>
        {t.entry.definition}
        <textarea
          value={definition}
          rows={3}
          onChange={(event) => setDefinition(event.target.value)}
        />
      </label>

      <label>
        {t.entry.synonyms}
        <input value={synonyms} onChange={(event) => setSynonyms(event.target.value)} />
        <span className="muted small">{t.entry.listHint}</span>
      </label>

      <label>
        {t.entry.nogo}
        <input value={nogo} onChange={(event) => setNogo(event.target.value)} />
        <span className="muted small">{t.entry.nogoHint} · {t.entry.listHint}</span>
      </label>

      <label>
        {t.entry.contextExample}
        <input
          value={contextExample}
          onChange={(event) => setContextExample(event.target.value)}
        />
      </label>

      <label>
        {t.entry.source}
        <input value={source} onChange={(event) => setSource(event.target.value)} />
      </label>

      {can('editor') && (
        <label>
          {t.entry.notes}
          <textarea value={notes} rows={2} onChange={(event) => setNotes(event.target.value)} />
          <span className="muted small">{t.entry.notesHint}</span>
        </label>
      )}

      {conflict ? <p className="error" role="alert">{t.entry.savedConflict}</p> : <ErrorMessage error={error} />}

      <div className="row">
        <button type="submit" className="button" disabled={busy}>
          {t.common.save}
        </button>
        <button type="button" className="button button--quiet" onClick={onCancel}>
          {t.common.cancel}
        </button>
      </div>
    </form>
  )
}

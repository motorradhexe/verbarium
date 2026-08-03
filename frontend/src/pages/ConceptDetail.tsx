import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { ApiError, api } from '../api/client'
import type { Concept, TermEntry, TransitionAction } from '../api/types'
import { useSession } from '../auth/SessionContext'
import { ErrorMessage, Loading } from '../components/Feedback'
import { LifecycleBadge, StatusBadge } from '../components/StatusBadge'
import { useI18n } from '../i18n'
import { EntryEditor } from './EntryEditor'

/** What to call a concept, which has no name of its own.
 *
 *  The entry in the interface language if there is one, otherwise the first
 *  entry — a detail page whose heading is only a status badge leaves the
 *  reader guessing what they are looking at.
 */
export function conceptTitle(entries: TermEntry[], locale: string): string | null {
  if (entries.length === 0) return null
  const preferred = entries.find((entry) => entry.language_code === locale)
  return (preferred ?? entries[0]).term
}

/** Which transitions to offer, given the entry's status and the role held.
 *
 *  The backend is the authority — it refuses anything else — but offering a
 *  button that always fails is its own kind of broken.
 */
export function availableActions(
  status: TermEntry['status'],
  can: (role: 'contributor' | 'reviewer' | 'approver') => boolean,
): TransitionAction[] {
  const actions: TransitionAction[] = []

  if (status === 'draft' && can('contributor')) actions.push('submit')
  if (status === 'proposed' && can('reviewer')) actions.push('start_review')
  if ((status === 'proposed' || status === 'in_review') && can('reviewer')) {
    actions.push('request_changes')
  }
  if (status === 'in_review' && can('approver')) actions.push('approve')
  if ((status === 'proposed' || status === 'in_review') && can('approver')) actions.push('reject')

  return actions
}

/** The two negative outcomes have to say why. → D6 */
const NEEDS_COMMENT: TransitionAction[] = ['request_changes', 'reject']

function TransitionControls({ entry, onDone }: { entry: TermEntry; onDone: () => void }) {
  const { t } = useI18n()
  const { can } = useSession()
  const [comment, setComment] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)

  const actions = availableActions(entry.status, can)
  if (actions.length === 0) return null

  async function run(action: TransitionAction) {
    setError(null)
    setBusy(true)
    try {
      await api.transitionTerm(entry.id, action, comment || undefined)
      setComment('')
      onDone()
    } catch (failure) {
      // The backend answers in English. For the one refusal the UI can
      // anticipate — a missing reason — it says so in the user's language;
      // everything else falls through to the backend's wording, which is
      // specific enough to be worth showing. See the note in STRUCTURE.md.
      if (
        failure instanceof ApiError &&
        failure.status === 422 &&
        NEEDS_COMMENT.includes(action)
      ) {
        setError(new ApiError(422, t.workflow.commentRequired))
      } else {
        setError(failure)
      }
    } finally {
      setBusy(false)
    }
  }

  const needsComment = actions.some((action) => NEEDS_COMMENT.includes(action))

  return (
    <div className="stack stack--tight">
      {needsComment && (
        <label>
          {t.workflow.commentLabel}
          <textarea
            value={comment}
            rows={2}
            onChange={(event) => setComment(event.target.value)}
          />
          <span className="muted small">{t.workflow.commentRequired}</span>
        </label>
      )}

      <div className="row">
        {actions.map((action) => (
          <button
            key={action}
            type="button"
            className={`button ${action === 'reject' ? 'button--danger' : ''}`}
            disabled={busy}
            onClick={() => void run(action)}
          >
            {t.workflow[action]}
          </button>
        ))}
      </div>

      <ErrorMessage error={error} />
    </div>
  )
}

function EntryPanel({ entry, onChanged }: { entry: TermEntry; onChanged: () => void }) {
  const { t } = useI18n()
  const { can } = useSession()
  const [editing, setEditing] = useState(false)
  const [comments, setComments] = useState<Awaited<ReturnType<typeof api.termComments>>>([])
  const [history, setHistory] = useState<Awaited<ReturnType<typeof api.termHistory>>>([])

  useEffect(() => {
    api.termComments(entry.id).then(setComments).catch(() => setComments([]))
    // Editors and above only; a 403 for everyone else is expected, not an error.
    if (can('editor')) {
      api.termHistory(entry.id).then(setHistory).catch(() => setHistory([]))
    }
  }, [entry.id, entry.version, entry.status, can])

  if (editing) {
    return (
      <EntryEditor
        entry={entry}
        onCancel={() => setEditing(false)}
        onSaved={() => {
          setEditing(false)
          onChanged()
        }}
      />
    )
  }

  return (
    <article className="panel">
      <header className="row row--spread">
        <h3>
          <span className="panel__lang">{entry.language_code.toUpperCase()}</span> {entry.term}
        </h3>
        <div className="row">
          <StatusBadge status={entry.status} />
          {entry.origin !== 'manual' && (
            <span className="badge badge--origin">
              {entry.origin === 'ai' ? t.entry.originAi : t.entry.originImport}
            </span>
          )}
          {can('editor') && (
            <button type="button" className="button button--quiet" onClick={() => setEditing(true)}>
              {t.entry.edit}
            </button>
          )}
        </div>
      </header>

      <dl className="fields">
        <dt>{t.entry.definition}</dt>
        <dd>{entry.definition || <span className="muted">{t.entry.noDefinition}</span>}</dd>

        {entry.synonyms.length > 0 && (
          <>
            <dt>{t.entry.synonyms}</dt>
            <dd>{entry.synonyms.join(', ')}</dd>
          </>
        )}

        {entry.nogo_alternatives.length > 0 && (
          <>
            <dt>{t.entry.nogo}</dt>
            <dd className="nogo">{entry.nogo_alternatives.join(', ')}</dd>
          </>
        )}

        {entry.context_example && (
          <>
            <dt>{t.entry.contextExample}</dt>
            <dd>{entry.context_example}</dd>
          </>
        )}

        {entry.source && (
          <>
            <dt>{t.entry.source}</dt>
            <dd>{entry.source}</dd>
          </>
        )}

        {entry.notes !== null && (
          <>
            <dt>{t.entry.notes}</dt>
            <dd className="notes">{entry.notes}</dd>
          </>
        )}
      </dl>

      <TransitionControls entry={entry} onDone={onChanged} />

      <details>
        <summary>{t.workflow.comments}</summary>
        {comments.length === 0 ? (
          <p className="muted small">{t.workflow.noComments}</p>
        ) : (
          <ul className="timeline">
            {comments.map((comment) => (
              <li key={comment.id}>
                <span className="muted small">
                  {new Date(comment.created_at).toLocaleString()}
                  {comment.transition ? ` · ${comment.transition}` : ''}
                </span>
                <p>{comment.body}</p>
              </li>
            ))}
          </ul>
        )}
      </details>

      {can('editor') && (
        <details>
          <summary>{t.workflow.history}</summary>
          {history.length === 0 ? (
            <p className="muted small">{t.workflow.noHistory}</p>
          ) : (
            <ul className="timeline">
              {history.map((change) => (
                <li key={change.id}>
                  <span className="muted small">
                    {new Date(change.changed_at).toLocaleString()}
                  </span>
                  <p>
                    {change.field === 'created' ? (
                      t.workflow.created
                    ) : (
                      <>
                        <strong>{change.field}</strong> {t.workflow.changedFrom}{' '}
                        <em>{change.old_value ?? t.common.none}</em> {t.workflow.changedTo}{' '}
                        <em>{change.new_value ?? t.common.none}</em>
                      </>
                    )}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </details>
      )}
    </article>
  )
}

export function ConceptDetail() {
  const { t, locale } = useI18n()
  const { can } = useSession()
  const { id } = useParams<{ id: string }>()
  const [concept, setConcept] = useState<Concept | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)
  const [addingLanguage, setAddingLanguage] = useState(false)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    try {
      setConcept(await api.getConcept(id))
      setError(null)
    } catch (failure) {
      setError(failure)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  if (loading) return <Loading />

  if (error instanceof ApiError && error.status === 404) {
    return (
      <div className="stack">
        <p className="muted">{t.concept.notFound}</p>
        <Link to="/">{t.concept.back}</Link>
      </div>
    )
  }

  if (!concept) return <ErrorMessage error={error} />

  return (
    <div className="stack">
      <Link to="/" className="muted small">
        ← {t.concept.back}
      </Link>

      <div className="row row--spread">
        <h1 className="row">
          {conceptTitle(concept.term_entries, locale) ?? t.list.concept}
          <StatusBadge status={concept.status} />
          <LifecycleBadge lifecycle={concept.lifecycle} />
        </h1>

        {can('editor') && (
          <div className="row">
            {concept.lifecycle === 'active' ? (
              <button
                type="button"
                className="button button--quiet"
                onClick={() => api.deprecateConcept(concept.id, null).then(load)}
              >
                {t.concept.deprecate}
              </button>
            ) : (
              <button
                type="button"
                className="button button--quiet"
                onClick={() => api.reactivateConcept(concept.id).then(load)}
              >
                {t.concept.reactivate}
              </button>
            )}
          </div>
        )}
      </div>

      <p className="muted small">{t.concept.rollupHint}</p>

      <p>
        <strong>{t.concept.domains}:</strong>{' '}
        {concept.domains.length > 0
          ? concept.domains.map((domain) => domain.name).join(', ')
          : t.concept.noDomains}
      </p>

      {concept.superseded_by_id && (
        <p>
          <strong>{t.concept.supersededBy}:</strong>{' '}
          <Link to={`/concepts/${concept.superseded_by_id}`}>{concept.superseded_by_id}</Link>
        </p>
      )}

      <ErrorMessage error={error} />

      <h2>{t.concept.entries}</h2>
      {concept.term_entries.map((entry) => (
        <EntryPanel key={entry.id} entry={entry} onChanged={load} />
      ))}

      {can('contributor') &&
        (addingLanguage ? (
          <EntryEditor
            conceptId={concept.id}
            onCancel={() => setAddingLanguage(false)}
            onSaved={() => {
              setAddingLanguage(false)
              void load()
            }}
          />
        ) : (
          <button type="button" className="button" onClick={() => setAddingLanguage(true)}>
            {t.concept.addLanguage}
          </button>
        ))}
    </div>
  )
}

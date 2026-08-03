import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../api/client'
import type { Domain } from '../api/types'
import { ErrorMessage } from '../components/Feedback'
import { useI18n } from '../i18n'
import { parseList } from './EntryEditor'

/** Creating a concept and its first entry in one step.
 *
 *  A concept with no term is not something anyone wants on purpose, and the
 *  backend accepts both in a single call.
 */
export function NewConcept() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [domains, setDomains] = useState<Domain[]>([])
  const [domainId, setDomainId] = useState('')
  const [languageCode, setLanguageCode] = useState('')
  const [term, setTerm] = useState('')
  const [definition, setDefinition] = useState('')
  const [synonyms, setSynonyms] = useState('')
  const [nogo, setNogo] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.listDomains().then(setDomains).catch(() => setDomains([]))
  }, [])

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const concept = await api.createConcept({
        domain_ids: domainId ? [domainId] : [],
        terms: [
          {
            language_code: languageCode.trim().toLowerCase(),
            term,
            definition: definition || null,
            synonyms: parseList(synonyms),
            nogo_alternatives: parseList(nogo),
          },
        ],
      })
      navigate(`/concepts/${concept.id}`)
    } catch (failure) {
      setError(failure)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="narrow">
      <h1>{t.list.newConcept}</h1>

      <form className="stack" onSubmit={submit}>
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
          <span className="muted small">{t.entry.nogoHint}</span>
        </label>

        <label>
          {t.list.domain}
          <select value={domainId} onChange={(event) => setDomainId(event.target.value)}>
            <option value="">{t.common.none}</option>
            {domains.map((domain) => (
              <option key={domain.id} value={domain.id}>
                {domain.name}
              </option>
            ))}
          </select>
        </label>

        <ErrorMessage error={error} />

        <div className="row">
          <button type="submit" className="button" disabled={busy}>
            {t.common.save}
          </button>
          <button type="button" className="button button--quiet" onClick={() => navigate('/')}>
            {t.common.cancel}
          </button>
        </div>
      </form>
    </div>
  )
}

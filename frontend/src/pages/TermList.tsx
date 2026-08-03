import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { api, type ConceptFilters } from '../api/client'
import type { ConceptPage, Domain, TermStatus } from '../api/types'
import { ErrorMessage, Loading } from '../components/Feedback'
import { LifecycleBadge, StatusBadge } from '../components/StatusBadge'
import { useI18n } from '../i18n'

const PAGE_SIZE = 25
const STATUSES: TermStatus[] = ['draft', 'proposed', 'in_review', 'approved', 'rejected']

/** Filters live in the URL so a filtered view can be linked and survives a
 *  reload — the state a colleague is looking at is the state they can send. */
function filtersFromParams(params: URLSearchParams): ConceptFilters {
  return {
    query: params.get('query') ?? undefined,
    language: params.get('language') ?? undefined,
    missing_language: params.get('missing_language') ?? undefined,
    status: params.getAll('status'),
    domain_id: params.getAll('domain_id'),
    lifecycle: params.get('lifecycle') ?? undefined,
    limit: PAGE_SIZE,
    offset: Number(params.get('offset') ?? 0),
  }
}

export function TermList() {
  const { t } = useI18n()
  const [params, setParams] = useSearchParams()
  const [page, setPage] = useState<ConceptPage | null>(null)
  const [domains, setDomains] = useState<Domain[]>([])
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)

  const filters = useMemo(() => filtersFromParams(params), [params])
  const offset = filters.offset ?? 0

  // Typing updates the URL only once the user pauses; without this every
  // keystroke would be a request and a history entry.
  const [searchDraft, setSearchDraft] = useState(filters.query ?? '')
  useEffect(() => {
    if ((filters.query ?? '') === searchDraft) return
    const timer = setTimeout(() => update({ query: searchDraft }), 300)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchDraft])

  /** Every language that appears on this page, so the table has one column
   *  each. Driven by the data rather than a fixed pair, because the workspace
   *  chooses its languages. → D14 */
  const columns = useMemo(() => {
    const seen = new Set<string>()
    for (const item of page?.items ?? []) {
      for (const code of Object.keys(item.languages)) seen.add(code)
    }
    const requested = [filters.language, filters.missing_language].filter(Boolean) as string[]
    for (const code of requested) seen.add(code)
    return [...seen].sort()
  }, [page, filters.language, filters.missing_language])

  useEffect(() => {
    api.listDomains().then(setDomains).catch(() => setDomains([]))
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setPage(await api.listConcepts(filters))
    } catch (failure) {
      setError(failure)
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    void load()
  }, [load])

  function update(changes: Record<string, string | string[] | null>) {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      next.delete(key)
      if (value === null || value === '') continue
      for (const item of Array.isArray(value) ? value : [value]) next.append(key, item)
    }
    // A filter change invalidates the page you were on — but paging itself
    // must keep the offset it just set.
    if (!('offset' in changes)) next.delete('offset')
    setParams(next)
  }

  const hasFilters = [...params.keys()].some((key) => key !== 'offset')
  const total = page?.total ?? 0

  return (
    <div className="stack">
      <div className="row row--spread">
        <h1>{t.list.title}</h1>
        <Link to="/concepts/new" className="button">
          {t.list.newConcept}
        </Link>
      </div>

      <form className="filters" onSubmit={(event) => event.preventDefault()}>
        <label className="filters__search">
          {t.list.search}
          <input
            type="search"
            value={searchDraft}
            placeholder={t.list.searchHint}
            onChange={(event) => setSearchDraft(event.target.value)}
          />
        </label>

        <label>
          {t.list.hasLanguage}
          <input
            value={filters.language ?? ''}
            placeholder="de"
            maxLength={2}
            className="input--code"
            onChange={(event) => update({ language: event.target.value })}
          />
        </label>

        <label title={t.list.missingLanguageHint}>
          {t.list.missingLanguage}
          <input
            value={filters.missing_language ?? ''}
            placeholder="en"
            maxLength={2}
            className="input--code"
            onChange={(event) => update({ missing_language: event.target.value })}
          />
        </label>

        <label>
          {t.list.status}
          <select
            value={filters.status?.[0] ?? ''}
            onChange={(event) => update({ status: event.target.value || null })}
          >
            <option value="">{t.common.none}</option>
            {STATUSES.map((status) => (
              <option key={status} value={status}>
                {t.status[status]}
              </option>
            ))}
          </select>
        </label>

        <label>
          {t.list.domain}
          <select
            value={filters.domain_id?.[0] ?? ''}
            onChange={(event) => update({ domain_id: event.target.value || null })}
          >
            <option value="">{t.common.none}</option>
            {domains.map((domain) => (
              <option key={domain.id} value={domain.id}>
                {domain.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          {t.list.lifecycle}
          <select
            value={filters.lifecycle ?? ''}
            onChange={(event) => update({ lifecycle: event.target.value || null })}
          >
            <option value="">{t.common.none}</option>
            <option value="active">{t.lifecycle.active}</option>
            <option value="deprecated">{t.lifecycle.deprecated}</option>
          </select>
        </label>

        {hasFilters && (
          <button
            type="button"
            className="button button--quiet"
            onClick={() => {
              setSearchDraft('')
              setParams({})
            }}
          >
            {t.list.clearFilters}
          </button>
        )}
      </form>

      <ErrorMessage error={error} />

      {loading && <Loading />}

      {!loading && page && page.items.length === 0 && (
        <p className="muted">{hasFilters ? t.list.empty : t.list.emptyUnfiltered}</p>
      )}

      {!loading && page && page.items.length > 0 && (
        <>
          <p className="muted small">
            {total} {t.list.resultCount}
          </p>

          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>{t.list.status}</th>
                  {columns.map((code) => (
                    <th key={code}>{code.toUpperCase()}</th>
                  ))}
                  <th>{t.list.domains}</th>
                </tr>
              </thead>
              <tbody>
                {page.items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <StatusBadge status={item.status} />
                      <LifecycleBadge lifecycle={item.lifecycle} />
                    </td>

                    {columns.map((code) => {
                      const cell = item.languages[code]
                      return (
                        <td key={code}>
                          {cell ? (
                            <Link to={`/concepts/${item.id}`} className="cell">
                              <span className="cell__term">{cell.term}</span>
                              <StatusBadge status={cell.status} />
                            </Link>
                          ) : (
                            // The gap is the point of this view: an empty
                            // cell is what the "language missing" filter
                            // finds. → D12
                            <span className="cell cell--gap">{t.status.missing}</span>
                          )}
                        </td>
                      )
                    })}

                    <td className="muted small">
                      {item.domains.map((domain) => domain.name).join(', ') || t.common.none}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="row row--spread">
            <button
              type="button"
              className="button button--quiet"
              disabled={offset === 0}
              onClick={() => update({ offset: String(Math.max(0, offset - PAGE_SIZE)) })}
            >
              {t.list.previous}
            </button>
            <span className="muted small">
              {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} {t.common.of} {total}
            </span>
            <button
              type="button"
              className="button button--quiet"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => update({ offset: String(offset + PAGE_SIZE) })}
            >
              {t.list.next}
            </button>
          </div>
        </>
      )}
    </div>
  )
}

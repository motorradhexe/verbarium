/** Thin fetch wrapper around the backend.
 *
 *  Relative URLs throughout: the dev server proxies `/api` to the backend, and
 *  in production both are served from the same origin. The session cookie is
 *  HTTP-only, so there is no token to attach — `credentials: same-origin` is
 *  all that is needed.
 */

import type {
  ChangeHistoryEntry,
  Concept,
  ConceptPage,
  Domain,
  ReviewComment,
  TermEntry,
  TransitionAction,
  UserProfile,
} from './types'

export class ApiError extends Error {
  constructor(
    readonly status: number,
    /** The backend's `detail`, or a fallback. Safe to show to a user. */
    readonly detail: string,
  ) {
    super(`${status}: ${detail}`)
    this.name = 'ApiError'
  }

  /** Not signed in, or the session expired. */
  get isUnauthenticated(): boolean {
    return this.status === 401
  }

  /** Signed in, but the role is not enough. */
  get isForbidden(): boolean {
    return this.status === 403
  }

  /** Someone else changed the entity first, or the workflow refused the move. */
  get isConflict(): boolean {
    return this.status === 409
  }
}

/** Pull a readable message out of whatever the backend returned.
 *
 *  FastAPI answers validation errors with a list of objects rather than a
 *  string, so a naive `detail` would render as "[object Object]".
 */
export function extractDetail(payload: unknown, fallback: string): string {
  if (typeof payload !== 'object' || payload === null) return fallback

  const detail = (payload as { detail?: unknown }).detail
  if (typeof detail === 'string') return detail

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item !== 'object' || item === null) return null
        const { loc, msg } = item as { loc?: unknown[]; msg?: string }
        if (!msg) return null
        const field = Array.isArray(loc) ? loc.filter((part) => part !== 'body').join('.') : ''
        return field ? `${field}: ${msg}` : msg
      })
      .filter((message): message is string => Boolean(message))

    if (messages.length > 0) return messages.join('; ')
  }

  return fallback
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    credentials: 'same-origin',
    headers: {
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...init.headers,
    },
  })

  if (!response.ok) {
    let payload: unknown = null
    try {
      payload = await response.json()
    } catch {
      // A response without a JSON body — the status still tells us enough.
    }
    throw new ApiError(response.status, extractDetail(payload, response.statusText))
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

function query(params: Record<string, string | string[] | number | undefined>): string {
  const search = new URLSearchParams()

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === '') continue
    if (Array.isArray(value)) {
      for (const item of value) search.append(key, item)
    } else {
      search.append(key, String(value))
    }
  }

  const rendered = search.toString()
  return rendered ? `?${rendered}` : ''
}

export interface ConceptFilters {
  /** Index signature so the filters can be handed straight to `query`. */
  [key: string]: string | string[] | number | undefined
  query?: string
  language?: string
  missing_language?: string
  status?: string[]
  domain_id?: string[]
  lifecycle?: string
  assignee_id?: string
  limit?: number
  offset?: number
}

export const api = {
  setupStatus: () => request<{ completed: boolean }>('/setup'),
  runSetup: (body: unknown) =>
    request<UserProfile>('/setup', { method: 'POST', body: JSON.stringify(body) }),

  login: (email: string, password: string) =>
    request<UserProfile>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  me: () => request<UserProfile>('/auth/me'),

  listDomains: () => request<Domain[]>('/domains'),
  createDomain: (name: string) =>
    request<Domain>('/domains', { method: 'POST', body: JSON.stringify({ name }) }),

  listConcepts: (filters: ConceptFilters) => request<ConceptPage>(`/concepts${query(filters)}`),
  getConcept: (id: string) => request<Concept>(`/concepts/${id}`),
  createConcept: (body: unknown) =>
    request<Concept>('/concepts', { method: 'POST', body: JSON.stringify(body) }),
  updateConcept: (id: string, version: number, domainIds: string[]) =>
    request<Concept>(`/concepts/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ version, domain_ids: domainIds }),
    }),
  deprecateConcept: (id: string, supersededBy: string | null) =>
    request<Concept>(`/concepts/${id}/deprecate`, {
      method: 'POST',
      body: JSON.stringify({ superseded_by_id: supersededBy }),
    }),
  reactivateConcept: (id: string) =>
    request<Concept>(`/concepts/${id}/reactivate`, { method: 'POST' }),
  addTerm: (conceptId: string, body: unknown) =>
    request<TermEntry>(`/concepts/${conceptId}/terms`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  updateTerm: (id: string, version: number, fields: Record<string, unknown>) =>
    request<TermEntry>(`/terms/${id}`, {
      method: 'PATCH',
      // The version travels with every write so a stale edit is refused
      // rather than silently overwriting someone else's. → D4
      body: JSON.stringify({ version, ...fields }),
    }),
  transitionTerm: (id: string, action: TransitionAction, comment?: string) =>
    request<TermEntry>(`/terms/${id}/transition`, {
      method: 'POST',
      body: JSON.stringify({ action, comment: comment ?? null }),
    }),
  assignTerm: (id: string, assigneeId: string | null) =>
    request<TermEntry>(`/terms/${id}/assignee`, {
      method: 'POST',
      body: JSON.stringify({ assignee_id: assigneeId }),
    }),
  termComments: (id: string) => request<ReviewComment[]>(`/terms/${id}/comments`),
  termHistory: (id: string) => request<ChangeHistoryEntry[]>(`/terms/${id}/history`),

  listUsers: () => request<UserProfile[]>('/users'),
}

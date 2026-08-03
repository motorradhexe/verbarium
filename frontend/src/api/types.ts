/** Mirrors the backend schemas. Kept by hand — the API is small enough that
 *  a generator would cost more than it saves. */

export type Role = 'viewer' | 'contributor' | 'editor' | 'reviewer' | 'approver' | 'admin'

export const ROLE_ORDER: Role[] = [
  'viewer',
  'contributor',
  'editor',
  'reviewer',
  'approver',
  'admin',
]

/** Roles are cumulative — an Approver can do everything an Editor can. */
export function canActAs(held: Role, required: Role): boolean {
  return ROLE_ORDER.indexOf(held) >= ROLE_ORDER.indexOf(required)
}

export type TermStatus = 'draft' | 'proposed' | 'in_review' | 'approved' | 'rejected'
export type Lifecycle = 'active' | 'deprecated'
export type Origin = 'manual' | 'ai' | 'import'
export type TransitionAction =
  | 'submit'
  | 'start_review'
  | 'request_changes'
  | 'approve'
  | 'reject'

export interface UserProfile {
  id: string
  email: string
  display_name: string
  role: Role
  is_active: boolean
  created_at: string
}

export interface TermEntry {
  id: string
  concept_id: string
  language_code: string
  term: string
  definition: string | null
  synonyms: string[]
  nogo_alternatives: string[]
  context_example: string | null
  source: string | null
  /** Null below the editorial roles. */
  notes: string | null
  status: TermStatus
  origin: Origin
  assignee_id: string | null
  created_by_id: string
  created_at: string
  updated_at: string
  version: number
}

export interface Domain {
  id: string
  name: string
}

export interface Concept {
  id: string
  lifecycle: Lifecycle
  superseded_by_id: string | null
  domains: Domain[]
  /** Derived from the entries: the least advanced language wins. */
  status: TermStatus | null
  term_entries: TermEntry[]
  created_by_id: string
  created_at: string
  updated_at: string
  version: number
}

export interface LanguageCell {
  term: string
  status: TermStatus
}

export interface ConceptListItem {
  id: string
  lifecycle: Lifecycle
  status: TermStatus | null
  domains: Domain[]
  languages: Record<string, LanguageCell>
  updated_at: string
}

export interface ConceptPage {
  items: ConceptListItem[]
  total: number
  limit: number
  offset: number
}

export interface ReviewComment {
  id: string
  term_entry_id: string
  author_id: string
  body: string
  transition: string | null
  created_at: string
}

export interface ChangeHistoryEntry {
  id: string
  field: string
  old_value: string | null
  new_value: string | null
  changed_by_id: string
  changed_at: string
}

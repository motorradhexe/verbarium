import { describe, expect, it } from 'vitest'

import { availableActions, conceptTitle } from './ConceptDetail'
import type { Role, TermEntry } from '../api/types'
import { canActAs } from '../api/types'

const asRole = (role: Role) => (required: 'contributor' | 'reviewer' | 'approver') =>
  canActAs(role, required)

function entry(fields: Partial<TermEntry>): TermEntry {
  return {
    id: 'x',
    concept_id: 'c',
    language_code: 'de',
    term: 'Espresso',
    definition: null,
    synonyms: [],
    nogo_alternatives: [],
    context_example: null,
    source: null,
    notes: null,
    status: 'draft',
    origin: 'manual',
    assignee_id: null,
    created_by_id: 'u',
    created_at: '',
    updated_at: '',
    version: 1,
    ...fields,
  }
}

describe('availableActions', () => {
  it('offers submitting a draft to anyone who may contribute', () => {
    expect(availableActions('draft', asRole('contributor'))).toEqual(['submit'])
  })

  it('offers nothing on a draft to a viewer', () => {
    expect(availableActions('draft', asRole('viewer'))).toEqual([])
  })

  it('lets a reviewer take a proposal into review or send it back', () => {
    expect(availableActions('proposed', asRole('reviewer'))).toEqual([
      'start_review',
      'request_changes',
    ])
  })

  it('does not offer approving to a reviewer', () => {
    // The backend refuses it; a button that always fails is its own bug.
    expect(availableActions('in_review', asRole('reviewer'))).not.toContain('approve')
  })

  it('offers approve and reject to an approver in review', () => {
    expect(availableActions('in_review', asRole('approver'))).toEqual([
      'request_changes',
      'approve',
      'reject',
    ])
  })

  it('offers nothing once an entry is approved or rejected', () => {
    expect(availableActions('approved', asRole('admin'))).toEqual([])
    expect(availableActions('rejected', asRole('admin'))).toEqual([])
  })
})

describe('conceptTitle', () => {
  it('prefers the entry in the interface language', () => {
    const entries = [entry({ language_code: 'de', term: 'Kaffeesatz' }), entry({ language_code: 'en', term: 'Coffee grounds' })]
    expect(conceptTitle(entries, 'en')).toBe('Coffee grounds')
  })

  it('falls back to the first entry when that language is missing', () => {
    expect(conceptTitle([entry({ language_code: 'de', term: 'Kaffeesatz' })], 'en')).toBe('Kaffeesatz')
  })

  it('has nothing to show for a concept without entries', () => {
    expect(conceptTitle([], 'de')).toBeNull()
  })
})

import { describe, expect, it } from 'vitest'

import { ApiError, extractDetail } from './client'
import { canActAs } from './types'

describe('extractDetail', () => {
  it('takes a plain string detail', () => {
    expect(extractDetail({ detail: 'No such concept' }, 'fallback')).toBe('No such concept')
  })

  it('flattens the list FastAPI returns for validation errors', () => {
    // Without this the UI would render "[object Object]" at the user.
    const payload = {
      detail: [
        { loc: ['body', 'admin_password'], msg: 'Password must be at least 12 characters long' },
      ],
    }

    expect(extractDetail(payload, 'fallback')).toBe(
      'admin_password: Password must be at least 12 characters long',
    )
  })

  it('joins several validation errors', () => {
    const payload = {
      detail: [
        { loc: ['body', 'term'], msg: 'Field required' },
        { loc: ['body', 'version'], msg: 'Field required' },
      ],
    }

    expect(extractDetail(payload, 'fallback')).toBe('term: Field required; version: Field required')
  })

  it('falls back when there is no usable detail', () => {
    expect(extractDetail(null, 'fallback')).toBe('fallback')
    expect(extractDetail({}, 'fallback')).toBe('fallback')
    expect(extractDetail({ detail: [] }, 'fallback')).toBe('fallback')
  })
})

describe('ApiError', () => {
  it('classifies the statuses the UI reacts to', () => {
    expect(new ApiError(401, 'x').isUnauthenticated).toBe(true)
    expect(new ApiError(403, 'x').isForbidden).toBe(true)
    expect(new ApiError(409, 'x').isConflict).toBe(true)
    expect(new ApiError(409, 'x').isForbidden).toBe(false)
  })
})

describe('canActAs', () => {
  it('treats roles as cumulative', () => {
    expect(canActAs('admin', 'editor')).toBe(true)
    expect(canActAs('approver', 'reviewer')).toBe(true)
    expect(canActAs('editor', 'editor')).toBe(true)
  })

  it('refuses a role that is too low', () => {
    expect(canActAs('contributor', 'editor')).toBe(false)
    expect(canActAs('viewer', 'admin')).toBe(false)
  })
})

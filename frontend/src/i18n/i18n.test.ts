import { describe, expect, it } from 'vitest'

import { de, en } from './strings'
import { detectLocale } from './index'

/** Every key present in one language must exist in the other, or a label
 *  silently renders as undefined. TypeScript enforces this at compile time;
 *  this catches it if the type ever loosens. */
function keyPaths(value: unknown, prefix = ''): string[] {
  if (typeof value !== 'object' || value === null) return [prefix]
  return Object.entries(value).flatMap(([key, nested]) =>
    keyPaths(nested, prefix ? `${prefix}.${key}` : key),
  )
}

describe('translations', () => {
  it('cover the same keys in both languages', () => {
    expect(keyPaths(en).sort()).toEqual(keyPaths(de).sort())
  })

  it('have no empty strings', () => {
    const empties = [...keyPaths(de), ...keyPaths(en)].filter((path) => path === '')
    expect(empties).toEqual([])
  })

  it('translate every term status', () => {
    for (const status of ['draft', 'proposed', 'in_review', 'approved', 'rejected'] as const) {
      expect(de.status[status]).toBeTruthy()
      expect(en.status[status]).toBeTruthy()
    }
  })
})

describe('detectLocale', () => {
  it('honours an explicit choice', () => {
    expect(detectLocale('de', ['en-US'])).toBe('de')
    expect(detectLocale('en', ['de-DE'])).toBe('en')
  })

  it('follows the browser when nothing is stored', () => {
    expect(detectLocale(null, ['de-AT', 'en'])).toBe('de')
    expect(detectLocale(null, ['fr-FR'])).toBe('en')
  })

  it('ignores a stored value that is not a supported language', () => {
    expect(detectLocale('klingon', ['de'])).toBe('de')
  })
})

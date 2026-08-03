import { describe, expect, it } from 'vitest'

import { formatList, parseList } from './EntryEditor'

describe('comma-separated lists', () => {
  it('trims and drops empties', () => {
    // A trailing comma is what people actually type.
    expect(parseList('Kaffee Crème, Crema,')).toEqual(['Kaffee Crème', 'Crema'])
    expect(parseList('  ')).toEqual([])
  })

  it('round-trips', () => {
    const items = ['Espresso', 'Caffè']
    expect(parseList(formatList(items))).toEqual(items)
  })
})

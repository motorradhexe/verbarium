import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

import { LOCALES, type Locale, type Translations } from './strings'

const STORAGE_KEY = 'verbarium.locale'

export function detectLocale(stored: string | null, browser: readonly string[]): Locale {
  if (stored === 'de' || stored === 'en') return stored
  // The interface ships in German and English; anything else falls back.
  return browser.some((tag) => tag.toLowerCase().startsWith('de')) ? 'de' : 'en'
}

interface LocaleContextValue {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: Translations
}

const LocaleContext = createContext<LocaleContextValue | null>(null)

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setStoredLocale] = useState<Locale>(() =>
    detectLocale(localStorage.getItem(STORAGE_KEY), navigator.languages ?? [navigator.language]),
  )

  const setLocale = useCallback((next: Locale) => {
    localStorage.setItem(STORAGE_KEY, next)
    document.documentElement.lang = next
    setStoredLocale(next)
  }, [])

  const value = useMemo(
    () => ({ locale, setLocale, t: LOCALES[locale] }),
    [locale, setLocale],
  )

  document.documentElement.lang = locale

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
}

export function useI18n(): LocaleContextValue {
  const value = useContext(LocaleContext)
  if (value === null) throw new Error('useI18n must be used inside a LocaleProvider')
  return value
}

export type { Locale, Translations }

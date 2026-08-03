import type { ReactNode } from 'react'
import { Link, Outlet } from 'react-router-dom'

import { useSession } from '../auth/SessionContext'
import { useI18n } from '../i18n'
import type { Locale } from '../i18n'

/** The shell. Takes `children` for the pages that sit outside the router —
 *  login and setup — so the language switcher is reachable there too. */
export function Layout({ children }: { children?: ReactNode }) {
  const { t, locale, setLocale } = useI18n()
  const { user, signOut } = useSession()

  return (
    <div className="app">
      <header className="app__header">
        <Link to="/" className="app__brand">
          {t.appName}
        </Link>

        {user && (
          <nav className="app__nav">
            <Link to="/">{t.nav.terms}</Link>
          </nav>
        )}

        <div className="app__account">
          <label className="visually-hidden" htmlFor="locale">
            {t.common.language}
          </label>
          <select
            id="locale"
            value={locale}
            onChange={(event) => setLocale(event.target.value as Locale)}
          >
            <option value="de">Deutsch</option>
            <option value="en">English</option>
          </select>

          {user && (
            <>
              <span className="app__user" title={`${t.nav.signedInAs} ${user.email}`}>
                {user.display_name} · {t.role[user.role]}
              </span>
              <button type="button" className="button button--quiet" onClick={() => void signOut()}>
                {t.nav.signOut}
              </button>
            </>
          )}
        </div>
      </header>

      <main className="app__main">{children ?? <Outlet />}</main>
    </div>
  )
}

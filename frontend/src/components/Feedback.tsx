import { ApiError } from '../api/client'
import { useI18n } from '../i18n'

export function Loading() {
  const { t } = useI18n()
  return <p className="muted" role="status">{t.common.loading}</p>
}

/** Renders whatever went wrong in terms a user can act on.
 *
 *  The backend's `detail` is written for people — "requires the approver role
 *  or higher", "you edited version 1, it is now at 2" — so showing it beats
 *  replacing it with a generic message.
 */
export function ErrorMessage({ error }: { error: unknown }) {
  const { t } = useI18n()

  if (!error) return null

  let message = t.errors.generic
  if (error instanceof ApiError) {
    message = error.detail || (error.isForbidden ? t.errors.forbidden : t.errors.generic)
  } else if (error instanceof TypeError) {
    // fetch rejects with a TypeError when it cannot reach the server at all.
    message = t.errors.offline
  }

  return (
    <p className="error" role="alert">
      {message}
    </p>
  )
}

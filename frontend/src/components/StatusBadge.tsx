import type { Lifecycle, TermStatus } from '../api/types'
import { useI18n } from '../i18n'

/** Status as a badge, never as colour alone — the label carries the meaning
 *  so it survives greyscale printing and colour blindness. */
export function StatusBadge({ status }: { status: TermStatus | null }) {
  const { t } = useI18n()

  if (status === null) {
    return <span className="badge badge--empty">{t.common.none}</span>
  }

  return <span className={`badge badge--${status}`}>{t.status[status]}</span>
}

export function LifecycleBadge({ lifecycle }: { lifecycle: Lifecycle }) {
  const { t } = useI18n()

  if (lifecycle === 'active') return null
  return <span className="badge badge--deprecated">{t.lifecycle.deprecated}</span>
}

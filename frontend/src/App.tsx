import { useEffect, useState } from 'react'

type BackendState = 'checking' | 'online' | 'offline'

export default function App() {
  const [backend, setBackend] = useState<BackendState>('checking')

  useEffect(() => {
    const controller = new AbortController()

    fetch('/health', { signal: controller.signal })
      .then((response) => (response.ok ? setBackend('online') : setBackend('offline')))
      .catch(() => {
        if (!controller.signal.aborted) {
          setBackend('offline')
        }
      })

    return () => controller.abort()
  }, [])

  return (
    <main className="shell">
      <h1>Verbarium</h1>
      <p className="tagline">Terminology Management for People Who Care About Words</p>
      <p className="note">
        Project scaffolding. No features yet — see <code>REQUIREMENTS.md</code> for the roadmap.
      </p>
      <p className={`status status--${backend}`}>
        Backend:{' '}
        {backend === 'checking' ? 'checking…' : backend === 'online' ? 'reachable' : 'unreachable'}
      </p>
    </main>
  )
}

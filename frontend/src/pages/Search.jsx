import { useRef, useState } from 'react'
import { api } from '../lib/api.js'
import { useI18n } from '../i18n/I18nContext.jsx'
import Markdown from '../lib/Markdown.jsx'

export default function Search() {
  const { t } = useI18n()
  const [q, setQ] = useState('')
  const [results, setResults] = useState(null)
  const timerRef = useRef(null)
  const requestSeq = useRef(0)

  function onChange(value) {
    setQ(value)
    clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      if (!value) return setResults(null)
      // Guard against out-of-order responses: only the most recently
      // *sent* request is allowed to update state, even if an earlier,
      // shorter query happens to resolve later over the network.
      const seq = ++requestSeq.current
      api.listEntries({ q: value }).then((data) => {
        if (seq === requestSeq.current) setResults(data)
      })
    }, 200)
  }

  return (
    <div className="p-8 max-w-3xl">
      <input
        value={q}
        onChange={(e) => onChange(e.target.value)}
        placeholder={t.search.placeholder}
        autoFocus
        className="w-full bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg px-4 py-3 text-sm outline-none focus:border-[var(--color-gold)] mb-6"
      />

      {results && (
        <p className="text-sm text-[var(--color-text-secondary)] mb-4">
          {t.search.resultsFor} <b className="text-[var(--color-gold-soft)] font-[family-name:var(--font-mono)]">"{q}"</b> — {results.length}
        </p>
      )}

      {results && results.length === 0 && (
        <p className="text-sm text-[var(--color-text-tertiary)]">{t.search.empty}</p>
      )}

      <div className="flex flex-col">
        {(results || []).map((e) => (
          <div key={e.id} className="border-b border-[var(--color-border)] py-4">
            <div className="font-semibold text-sm mb-1">{e.title || e.body.slice(0, 60)}</div>
            <div className="text-xs text-[var(--color-text-tertiary)] font-[family-name:var(--font-mono)] mb-1.5">
              {e.timestamp.slice(0, 10)} · {e.machine}{e.project_name ? ` · ${e.project_name}` : ''}
            </div>
            <Markdown text={e.body} className="text-sm text-[var(--color-text-secondary)]" />
          </div>
        ))}
      </div>
    </div>
  )
}

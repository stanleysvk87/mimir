import { useRef, useState } from 'react'
import { api } from '../lib/api.js'
import { useI18n } from '../i18n/I18nContext.jsx'
import Markdown from '../lib/Markdown.jsx'
import { looksStructured } from '../lib/textShape.js'

const SNIPPET_RADIUS = 160
const SNIPPET_MAX_LEN = 320

function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// Cuts a short window around the first hit of `query` (falls back to the
// start of the body if there's no literal match, e.g. it matched via
// accent-folding) and wraps every occurrence of the query in <mark> --
// marked() passes inline HTML through untouched, so this survives the
// markdown render.
function buildSnippet(body, query) {
  const trimmedQuery = query.trim()
  let windowText = body
  if (body.length > SNIPPET_MAX_LEN) {
    const idx = trimmedQuery ? body.toLowerCase().indexOf(trimmedQuery.toLowerCase()) : -1
    if (idx === -1) {
      windowText = body.slice(0, SNIPPET_MAX_LEN) + '…'
    } else {
      const start = Math.max(0, idx - SNIPPET_RADIUS)
      const end = Math.min(body.length, idx + trimmedQuery.length + SNIPPET_RADIUS)
      windowText = (start > 0 ? '…' : '') + body.slice(start, end) + (end < body.length ? '…' : '')
    }
  }
  if (!trimmedQuery) return windowText
  return windowText.replace(new RegExp(`(${escapeRegExp(trimmedQuery)})`, 'gi'), '<mark>$1</mark>')
}

export default function Search() {
  const { t } = useI18n()
  const [q, setQ] = useState('')
  const [results, setResults] = useState(null)
  const [expanded, setExpanded] = useState(() => new Set())
  const timerRef = useRef(null)
  const requestSeq = useRef(0)

  function toggleExpanded(id) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

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
        {(results || []).map((e) => {
          const isLong = e.body.length > SNIPPET_MAX_LEN
          const isExpanded = expanded.has(e.id)
          const shown = isExpanded ? e.body : buildSnippet(e.body, q)
          return (
            <div key={e.id} className="border-b border-[var(--color-border)] py-4">
              <div className="font-semibold text-sm mb-1">{e.title || e.body.slice(0, 60)}</div>
              <div className="text-xs text-[var(--color-text-tertiary)] font-[family-name:var(--font-mono)] mb-1.5">
                {e.timestamp.slice(0, 10)} · {e.machine}{e.project_name ? ` · ${e.project_name}` : ''}
              </div>
              <Markdown
                text={shown}
                className={`text-sm text-[var(--color-text-secondary)] search-snippet ${looksStructured(e.body) ? 'font-[family-name:var(--font-mono)]' : ''}`}
              />
              {isLong && (
                <button
                  onClick={() => toggleExpanded(e.id)}
                  className="text-xs text-[var(--color-text-tertiary)] hover:text-[var(--color-gold-soft)] mt-1.5"
                >
                  {isExpanded ? t.search.showLess : t.search.showMore}
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

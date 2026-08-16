import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api.js'
import { useI18n } from '../i18n/I18nContext.jsx'

export default function Terminal() {
  const { t } = useI18n()
  const [tab, setTab] = useState('search') // search | review
  const [q, setQ] = useState('')
  const [results, setResults] = useState(null)
  const [reviewQueue, setReviewQueue] = useState([])
  const [reviewLoading, setReviewLoading] = useState(false)
  const [hasAnyData, setHasAnyData] = useState(null) // null = not checked yet
  const timerRef = useRef(null)
  const requestSeq = useRef(0)

  useEffect(() => {
    api.listTerminalSessions({ limit: 1 }).then((sessions) => setHasAnyData(sessions.length > 0))
  }, [])

  function onChange(value) {
    setQ(value)
    clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      if (!value) return setResults(null)
      const seq = ++requestSeq.current
      api.terminalSearch(value).then((data) => {
        if (seq === requestSeq.current) setResults(data)
      })
    }, 200)
  }

  function loadReviewQueue() {
    setReviewLoading(true)
    api.needsReviewList().then(setReviewQueue).finally(() => setReviewLoading(false))
  }

  useEffect(() => {
    if (tab === 'review') loadReviewQueue()
  }, [tab])

  async function approve(chunkId, editedText) {
    await api.approveChunk(chunkId, editedText)
    setReviewQueue((q) => q.filter((c) => c.id !== chunkId))
  }

  return (
    <div className="p-8 max-w-3xl">
      <div className="flex gap-1 mb-6">
        <button
          onClick={() => setTab('search')}
          className={`px-3 py-1.5 rounded-lg text-sm ${tab === 'search' ? 'bg-white/10 text-[var(--color-text-primary)]' : 'text-[var(--color-text-tertiary)] hover:bg-white/5'}`}
        >
          {t.terminal.searchTab}
        </button>
        <button
          onClick={() => setTab('review')}
          className={`px-3 py-1.5 rounded-lg text-sm ${tab === 'review' ? 'bg-white/10 text-[var(--color-text-primary)]' : 'text-[var(--color-text-tertiary)] hover:bg-white/5'}`}
        >
          {t.terminal.needsReviewTab}{reviewQueue.length > 0 ? ` (${reviewQueue.length})` : ''}
        </button>
      </div>

      {tab === 'search' && (
        <>
          <input
            value={q}
            onChange={(e) => onChange(e.target.value)}
            placeholder={t.terminal.searchPlaceholder}
            autoFocus
            className="w-full bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg px-4 py-3 text-sm outline-none focus:border-[var(--color-gold)] mb-6"
          />

          {hasAnyData === false && (
            <p className="text-sm text-[var(--color-text-tertiary)] mb-4">{t.terminal.noDataYet}</p>
          )}

          {hasAnyData !== false && results && (
            <p className="text-sm text-[var(--color-text-secondary)] mb-4">
              {results.length} {results.length === 1 ? t.terminal.matchWord : t.terminal.matchWordPlural}
            </p>
          )}

          <div className="flex flex-col">
            {(results || []).map((r) => (
              <div key={r.chunk_id} className="border-b border-[var(--color-border)] py-4">
                <div className="text-xs text-[var(--color-text-tertiary)] font-[family-name:var(--font-mono)] mb-1.5">
                  {r.started_at.slice(0, 16).replace('T', ' ')} · {r.host} · tmux {r.tmux_session_name}
                  {r.project_name ? ` · ${r.project_name}` : ''}
                </div>
                <pre className="text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap font-[family-name:var(--font-mono)] leading-relaxed">
                  {r.snippet}
                </pre>
              </div>
            ))}
            {hasAnyData !== false && results && results.length === 0 && (
              <p className="text-sm text-[var(--color-text-tertiary)]">{t.terminal.nothingFound}</p>
            )}
          </div>
        </>
      )}

      {tab === 'review' && (
        <div className="flex flex-col gap-4">
          <p className="text-sm text-[var(--color-text-secondary)]">
            {t.terminal.reviewIntro}
          </p>
          {reviewLoading && <p className="text-sm text-[var(--color-text-tertiary)]">{t.terminal.loading}</p>}
          {!reviewLoading && reviewQueue.length === 0 && (
            <p className="text-sm text-[var(--color-text-tertiary)]">{t.terminal.nothingWaiting}</p>
          )}
          {reviewQueue.map((c) => (
            <ReviewCard key={c.id} chunk={c} onApprove={approve} />
          ))}
        </div>
      )}
    </div>
  )
}

function ReviewCard({ chunk, onApprove }) {
  const { t } = useI18n()
  const [text, setText] = useState(chunk.text)
  const [busy, setBusy] = useState(false)

  return (
    <div className="bg-[var(--color-panel)] border border-[var(--color-border)] rounded-xl p-4">
      <div className="text-xs text-[var(--color-text-tertiary)] font-[family-name:var(--font-mono)] mb-2">
        {chunk.started_at.slice(0, 16).replace('T', ' ')} · session {chunk.session_id}
        {chunk.command_hint ? ` · ${chunk.command_hint}` : ''}
      </div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={Math.min(14, text.split('\n').length + 1)}
        className="w-full bg-[var(--color-panel-raised)] border border-[var(--color-border-strong)] rounded-lg p-3 text-xs font-[family-name:var(--font-mono)] outline-none focus:border-[var(--color-gold)] mb-3"
      />
      <button
        disabled={busy}
        onClick={async () => {
          setBusy(true)
          try {
            await onApprove(chunk.id, text)
          } finally {
            setBusy(false)
          }
        }}
        className="px-3 py-1.5 rounded-lg text-sm bg-[var(--color-gold)] text-[#241505] disabled:opacity-50"
      >
        {busy ? t.terminal.approving : t.terminal.approve}
      </button>
    </div>
  )
}

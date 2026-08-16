import { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api.js'
import { useI18n } from '../i18n/I18nContext.jsx'
import Markdown from '../lib/Markdown.jsx'
import { looksStructured } from '../lib/textShape.js'

const CATEGORY_KEYS = [
  'product',
  'topic-note',
  'systemd-service',
  'experiment',
  'midgardnet-variant',
  'client-work',
  'resolved',
]

// Bulk-imported by the MidgardOps notification scheduler every few
// minutes -- real value as raw audit trail, but at full weight in the
// default History view they bury the human-written entries. Collapsed
// separately below instead of dropped.
const AUTO_SOURCE_TYPE = 'midgardops_audit'

export default function Projects() {
  const { t } = useI18n()
  const [projects, setProjects] = useState([])
  const [category, setCategory] = useState('product')
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [entries, setEntries] = useState([])
  const [checklist, setChecklist] = useState([])
  const [timelineQ, setTimelineQ] = useState('')
  const [timeline, setTimeline] = useState(null)
  const [handoff, setHandoff] = useState(null)
  const [handoffLoading, setHandoffLoading] = useState(false)

  useEffect(() => {
    api.listProjects().then(setProjects)
  }, [])

  useEffect(() => {
    if (!selected) return
    setDetail(null)
    setTimeline(null)
    setTimelineQ('')
    setHandoff(null)
    api.getProject(selected.id).then(setDetail)
    api.listEntries({ projectId: selected.id, limit: 500 }).then(setEntries)
    api.listChecklist({ projectId: selected.id }).then(setChecklist)
  }, [selected])

  function runTimelineSearch(q) {
    setTimelineQ(q)
    if (!selected) return
    api.projectTimeline(selected.id, { q: q || undefined }).then(setTimeline)
  }

  function generateHandoff() {
    if (!selected) return
    setHandoffLoading(true)
    setHandoff(null)
    api.projectHandoff(selected.id).then(setHandoff).finally(() => setHandoffLoading(false))
  }

  const counts = useMemo(() => {
    const c = {}
    for (const p of projects) c[p.category] = (c[p.category] || 0) + 1
    return c
  }, [projects])

  const visible = useMemo(() => projects.filter((p) => p.category === category), [projects, category])
  const humanEntries = useMemo(() => entries.filter((e) => e.source_type !== AUTO_SOURCE_TYPE), [entries])
  const autoEntries = useMemo(() => entries.filter((e) => e.source_type === AUTO_SOURCE_TYPE), [entries])

  return (
    <div className="flex">
      <div className="w-64 border-r border-[var(--color-border)] p-5 flex-none sticky top-0 h-screen overflow-y-auto">
        <h2 className="text-xs uppercase tracking-wide text-[var(--color-text-tertiary)] mb-3">{t.projects.header}</h2>
        <div className="flex flex-wrap gap-1 mb-4">
          {CATEGORY_KEYS.filter((key) => counts[key]).map((key) => (
            <button
              key={key}
              onClick={() => { setCategory(key); setSelected(null) }}
              className={`px-2 py-1 rounded-md text-xs ${category === key ? 'bg-white/10 text-[var(--color-text-primary)]' : 'text-[var(--color-text-tertiary)] hover:bg-white/5'}`}
            >
              {t.projects.categories[key]} ({counts[key]})
            </button>
          ))}
        </div>
        <div className="flex flex-col gap-1">
          {visible.map((p) => (
            <button
              key={p.id}
              onClick={() => setSelected(p)}
              className={`text-left px-2.5 py-2 rounded-lg text-sm ${selected?.id === p.id ? 'bg-white/10 text-[var(--color-text-primary)]' : 'text-[var(--color-text-secondary)] hover:bg-white/5'}`}
            >
              {p.name}
            </button>
          ))}
          {visible.length === 0 && <p className="text-sm text-[var(--color-text-tertiary)]">{t.projects.noProjects}</p>}
        </div>
      </div>

      <div className="flex-1 p-8 max-w-3xl">
        {!selected && <p className="text-sm text-[var(--color-text-tertiary)]">{t.projects.pickProject}</p>}
        {selected && (
          <>
            <div className="flex items-center gap-2 text-xs text-[var(--color-success)] mb-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-success)]" />
              {selected.status}
            </div>
            <div className="flex items-center justify-between gap-3 mb-3">
              <h1 className="text-2xl">{selected.name}</h1>
              <button
                onClick={generateHandoff}
                disabled={handoffLoading}
                className="px-3 py-1.5 rounded-lg text-xs bg-[var(--color-panel-raised)] border border-[var(--color-border-strong)] text-[var(--color-text-secondary)] hover:border-[var(--color-gold)] disabled:opacity-50 flex-none"
              >
                {handoffLoading ? t.projects.writingBriefing : t.projects.generateHandoff}
              </button>
            </div>
            {selected.description && (
              <Markdown text={selected.description} className="text-sm text-[var(--color-text-secondary)] max-w-[70ch] mb-4" />
            )}
            {selected.key_paths && (
              <p className="text-xs text-[var(--color-text-tertiary)] font-[family-name:var(--font-mono)] mb-4">{selected.key_paths}</p>
            )}

            {handoff && (
              <div className="bg-[var(--color-panel)] border border-[var(--color-gold)]/30 rounded-xl p-4 mb-8">
                <div className="text-xs uppercase tracking-wide text-[var(--color-gold)] mb-2">{t.projects.handoffBriefing}</div>
                <Markdown text={handoff.briefing} className="text-sm text-[var(--color-text-secondary)] max-w-[70ch]" />
              </div>
            )}

            {selected.has_notes && (
              <details className="mb-8">
                <summary className="text-xs uppercase tracking-wide text-[var(--color-text-tertiary)] cursor-pointer select-none">
                  {t.projects.buildNotes}
                </summary>
                {detail ? (
                  <Markdown text={detail.notes} className="text-sm text-[var(--color-text-secondary)] max-w-[70ch] mt-3" />
                ) : (
                  <p className="text-sm text-[var(--color-text-tertiary)] mt-3">{t.projects.loading}</p>
                )}
              </details>
            )}

            <h2 className="text-xs uppercase tracking-wide text-[var(--color-text-tertiary)] mb-3 mt-7">
              {t.projects.timelineTitle} <span className="normal-case text-[var(--color-text-tertiary)]/70">{t.projects.timelineSubtitle}</span>
            </h2>
            <input
              value={timelineQ}
              onChange={(e) => runTimelineSearch(e.target.value)}
              placeholder={t.projects.timelinePlaceholder}
              className="w-full bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg px-4 py-2.5 text-sm outline-none focus:border-[var(--color-gold)] mb-4"
            />
            {timeline === null && (
              <button
                onClick={() => runTimelineSearch('')}
                className="text-xs text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)] mb-7"
              >
                {t.projects.loadFullTimeline}
              </button>
            )}
            {timeline !== null && (
              <div className="flex flex-col mb-7">
                {timeline.map((item) => (
                  <div key={`${item.type}-${item.id}`} className="border-b border-[var(--color-border)] py-3">
                    <div className="text-xs text-[var(--color-text-tertiary)] font-[family-name:var(--font-mono)] mb-1 flex items-center gap-1.5">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase ${
                        item.type === 'terminal' ? 'bg-[var(--color-panel-raised)] border border-[var(--color-border-strong)]'
                        : item.type === 'git_commit' ? 'bg-[var(--color-gold)]/10 border border-[var(--color-gold)]/25 text-[var(--color-gold)]'
                        : 'bg-white/5'
                      }`}>{item.type.replace('_', ' ')}</span>
                      {item.timestamp.slice(0, 16).replace('T', ' ')} · {item.machine}
                    </div>
                    <div className="text-sm font-semibold mb-0.5">{item.title}</div>
                    <p className="text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap line-clamp-3">{item.text}</p>
                  </div>
                ))}
                {timeline.length === 0 && <p className="text-sm text-[var(--color-text-tertiary)]">{t.projects.nothingMatched}</p>}
              </div>
            )}

            <h2 className="text-xs uppercase tracking-wide text-[var(--color-text-tertiary)] mb-3 mt-7">{t.projects.history}</h2>
            <div className="flex flex-col gap-3">
              {humanEntries.map((e) => (
                <div key={e.id} className="bg-[var(--color-panel)] border border-[var(--color-border)] rounded-xl p-4">
                  <div className="text-xs text-[var(--color-text-tertiary)] font-[family-name:var(--font-mono)] mb-1">
                    {e.timestamp.slice(0, 16).replace('T', ' ')} · {e.machine}
                  </div>
                  <h3 className="font-semibold text-sm mb-1">{e.title}</h3>
                  <Markdown
                    text={e.body}
                    className={`text-sm text-[var(--color-text-secondary)] ${looksStructured(e.body) ? 'font-[family-name:var(--font-mono)]' : ''}`}
                  />
                </div>
              ))}
              {humanEntries.length === 0 && <p className="text-sm text-[var(--color-text-tertiary)]">{t.projects.noEntries}</p>}
            </div>

            {autoEntries.length > 0 && (
              <details className="mt-4">
                <summary className="text-xs text-[var(--color-text-tertiary)] cursor-pointer select-none py-1">
                  {t.projects.autoNotifications.replace('{n}', autoEntries.length)}
                </summary>
                <div className="flex flex-col gap-3 mt-3">
                  {autoEntries.map((e) => (
                    <div key={e.id} className="bg-[var(--color-panel)] border border-[var(--color-border)] rounded-xl p-4 opacity-70">
                      <div className="text-xs text-[var(--color-text-tertiary)] font-[family-name:var(--font-mono)] mb-1">
                        {e.timestamp.slice(0, 16).replace('T', ' ')} · {e.machine}
                      </div>
                      <h3 className="font-semibold text-sm mb-1">{e.title}</h3>
                      <Markdown text={e.body} className="text-sm text-[var(--color-text-secondary)] font-[family-name:var(--font-mono)]" />
                    </div>
                  ))}
                </div>
              </details>
            )}

            <h2 className="text-xs uppercase tracking-wide text-[var(--color-text-tertiary)] mb-3 mt-7">{t.projects.openItems}</h2>
            <div className="flex flex-col">
              {checklist.map((c) => (
                <div key={c.id} className="flex items-start gap-2 py-2 border-t border-[var(--color-border)] first:border-t-0 first:pt-0 text-sm">
                  <span
                    className={`w-3.5 h-3.5 rounded mt-0.5 border ${c.status === 'done' ? 'bg-[var(--color-success)] border-[var(--color-success)]' : 'border-[var(--color-border-strong)]'}`}
                  />
                  <span className={c.status === 'done' ? 'line-through text-[var(--color-text-tertiary)]' : ''}>{c.text}</span>
                </div>
              ))}
              {checklist.length === 0 && <p className="text-sm text-[var(--color-text-tertiary)]">{t.projects.nothingOpen}</p>}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

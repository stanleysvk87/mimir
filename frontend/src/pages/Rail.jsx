import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api.js'
import { useI18n } from '../i18n/I18nContext.jsx'

function entryLink(entry) {
  return `/?day=${entry.timestamp.slice(0, 10)}&entry=${entry.id}`
}

function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime()
  const mins = Math.round(diffMs / 60000)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.round(hours / 24)}d ago`
}

export default function Rail() {
  const { t } = useI18n()
  const [sync, setSync] = useState([])
  const [onThisDay, setOnThisDay] = useState([])
  const [reminders, setReminders] = useState([])

  useEffect(() => {
    api.syncStatus().then(setSync)
    const monthDay = new Date().toISOString().slice(5, 10)
    api.onThisDay(monthDay).then(setOnThisDay)
    api.remindersDue().then(setReminders)
  }, [])

  return (
    <aside className="w-72 border-l border-[var(--color-border)] p-5 flex flex-col gap-5 flex-none sticky top-0 h-screen overflow-y-auto">
      <div className="bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-xl p-4">
        <h4 className="text-xs uppercase tracking-wide text-[var(--color-text-tertiary)] mb-3">{t.rail.onThisDay}</h4>
        {onThisDay.length === 0 ? (
          <p className="text-sm text-[var(--color-text-secondary)]">{t.rail.onThisDayEmpty}</p>
        ) : (
          <div className="flex flex-col gap-2">
            {onThisDay.map((e) => (
              <Link key={e.id} to={entryLink(e)} className="text-sm block hover:text-[var(--color-gold-soft)]">
                <span className="text-[var(--color-text-tertiary)] font-[family-name:var(--font-mono)] text-xs">
                  {e.timestamp.slice(0, 4)}
                </span>{' '}
                <span className="text-[var(--color-text-secondary)]">{e.title || e.body.slice(0, 60)}</span>
              </Link>
            ))}
          </div>
        )}
      </div>

      <div className="bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-xl p-4">
        <h4 className="text-xs uppercase tracking-wide text-[var(--color-text-tertiary)] mb-3">{t.rail.syncStatus}</h4>
        {sync.length === 0 && <p className="text-sm text-[var(--color-text-tertiary)]">{t.rail.syncStatusEmpty}</p>}
        {sync.map((s) => (
          <div key={s.machine} className="flex items-center justify-between text-sm py-1.5 border-t border-[var(--color-border)] first:border-t-0 first:pt-0">
            <span className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-success)]" />
              {s.machine}
            </span>
            <span className="text-xs text-[var(--color-text-secondary)] font-[family-name:var(--font-mono)]">{timeAgo(s.last_seen)}</span>
          </div>
        ))}
      </div>

      <div className="bg-[var(--color-panel-raised)] border border-[var(--color-border)] rounded-xl p-4">
        <h4 className="text-xs uppercase tracking-wide text-[var(--color-text-tertiary)] mb-3">{t.rail.reminders}</h4>
        {reminders.length === 0 && <p className="text-sm text-[var(--color-text-tertiary)]">{t.rail.remindersEmpty}</p>}
        {reminders.map((r) => (
          <Link
            key={r.id}
            to={entryLink(r)}
            className="block text-sm py-1.5 border-t border-[var(--color-border)] first:border-t-0 first:pt-0 hover:text-[var(--color-gold-soft)]"
          >
            <div className="font-semibold">{r.title}</div>
            <div className="text-xs text-[var(--color-warning)]">{t.rail.due} {r.follow_up_date}</div>
          </Link>
        ))}
      </div>
    </aside>
  )
}

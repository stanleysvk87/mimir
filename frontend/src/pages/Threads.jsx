import { useEffect, useState } from 'react'
import { api } from '../lib/api.js'
import { useI18n } from '../i18n/I18nContext.jsx'
import Markdown from '../lib/Markdown.jsx'

export default function Threads() {
  const { t } = useI18n()
  const [threads, setThreads] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [name, setName] = useState('')

  function reload() {
    api.listThreads().then(setThreads)
  }

  useEffect(reload, [])

  useEffect(() => {
    if (selected) api.getThread(selected.id).then(setDetail)
  }, [selected])

  async function create(e) {
    e.preventDefault()
    if (!name.trim()) return
    await api.createThread({ name })
    setName('')
    reload()
  }

  return (
    <div className="flex">
      <div className="w-64 border-r border-[var(--color-border)] p-5 flex-none sticky top-0 h-screen overflow-y-auto">
        <h2 className="text-xs uppercase tracking-wide text-[var(--color-text-tertiary)] mb-3">{t.threads.header}</h2>
        <form onSubmit={create} className="mb-4">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t.threads.newThreadPlaceholder}
            className="w-full bg-transparent border-b border-[var(--color-border)] pb-2 text-sm outline-none focus:border-[var(--color-gold)]"
          />
        </form>
        <div className="flex flex-col gap-1">
          {threads.map((th) => (
            <button
              key={th.id}
              onClick={() => setSelected(th)}
              className={`text-left px-2.5 py-2 rounded-lg text-sm flex justify-between ${selected?.id === th.id ? 'bg-white/10 text-[var(--color-text-primary)]' : 'text-[var(--color-text-secondary)] hover:bg-white/5'}`}
            >
              <span>{th.name}</span>
              <span className="text-xs text-[var(--color-text-tertiary)]">{th.entry_count}</span>
            </button>
          ))}
          {threads.length === 0 && <p className="text-sm text-[var(--color-text-tertiary)]">{t.threads.noThreads}</p>}
        </div>
      </div>

      <div className="flex-1 p-8 max-w-3xl">
        {!detail && <p className="text-sm text-[var(--color-text-tertiary)]">{t.threads.pickThread}</p>}
        {detail && (
          <>
            <h1 className="text-2xl mb-1">{detail.thread.name}</h1>
            {detail.thread.description && (
              <p className="text-sm text-[var(--color-text-secondary)] mb-6">{detail.thread.description}</p>
            )}
            <div className="flex flex-col gap-3">
              {detail.entries.map((e) => (
                <div key={e.id} className="bg-[var(--color-panel)] border border-[var(--color-border)] rounded-xl p-4">
                  <div className="text-xs text-[var(--color-text-tertiary)] font-[family-name:var(--font-mono)] mb-1">
                    {e.timestamp.slice(0, 10)} · {e.machine}{e.project_name ? ` · ${e.project_name}` : ''}
                  </div>
                  <h3 className="font-semibold text-sm mb-1">{e.title}</h3>
                  <Markdown text={e.body} className="text-sm text-[var(--color-text-secondary)]" />
                </div>
              ))}
              {detail.entries.length === 0 && (
                <p className="text-sm text-[var(--color-text-tertiary)]">{t.threads.noEntriesLinked}</p>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

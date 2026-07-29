import { useState } from 'react'
import { api } from '../lib/api.js'
import Markdown from '../lib/Markdown.jsx'

export default function Recall() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)

  async function ask(e) {
    e.preventDefault()
    if (!question.trim()) return
    const q = question
    setMessages((m) => [...m, { role: 'user', text: q }])
    setQuestion('')
    setLoading(true)
    try {
      const res = await api.aiRecall(q)
      setMessages((m) => [...m, { role: 'ai', text: res.answer, matched: res.matched_count }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl mb-6">AI Recall</h1>
      <div className="flex flex-col gap-5 mb-6">
        {messages.map((m, i) => (
          <div key={i} className="flex gap-2.5 items-start">
            <div
              className={`w-6.5 h-6.5 rounded-full flex-none flex items-center justify-center text-xs ${m.role === 'ai' ? 'bg-gradient-to-br from-[var(--color-gold)] to-[#6b4a24] text-[#1a0f04]' : 'bg-[var(--color-panel-raised)] border border-[var(--color-border-strong)] text-[var(--color-text-secondary)]'}`}
              style={{ width: '26px', height: '26px' }}
            >
              {m.role === 'ai' ? '✦' : 'you'}
            </div>
            {m.role === 'user' ? (
              <p className="text-sm pt-0.5">{m.text}</p>
            ) : (
              <div className="bg-[var(--color-panel)] border border-[var(--color-border)] rounded-xl p-4 text-sm text-[var(--color-text-secondary)] leading-relaxed">
                <Markdown text={m.text} />
                {typeof m.matched === 'number' && (
                  <div className="text-xs text-[var(--color-text-tertiary)] mt-2">
                    based on {m.matched} matching entries
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {loading && <p className="text-sm text-[var(--color-text-tertiary)]">Thinking…</p>}
      </div>

      <form onSubmit={ask} className="flex gap-2 items-center bg-[var(--color-panel)] border border-[var(--color-border)] rounded-xl px-3.5 py-2.5">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask anything from your history…"
          className="flex-1 bg-transparent outline-none text-sm"
        />
        <button type="submit" className="w-7 h-7 rounded-lg bg-[var(--color-gold)] text-[#241505] flex items-center justify-center">
          →
        </button>
      </form>
    </div>
  )
}

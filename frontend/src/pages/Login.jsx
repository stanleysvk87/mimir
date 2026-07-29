import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api.js'
import { useI18n } from '../i18n/I18nContext.jsx'

export default function Login() {
  const { t } = useI18n()
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    try {
      await api.login(password)
      navigate('/')
    } catch {
      setError(t.login.error)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={onSubmit} className="w-full max-w-xs flex flex-col gap-4">
        <div className="flex flex-col items-center gap-2 mb-2">
          <svg viewBox="0 0 24 24" className="w-9 h-9">
            <circle cx="12" cy="12" r="9.25" stroke="var(--color-gold)" strokeWidth="1.3" fill="none" />
            <circle cx="12" cy="12" r="4.5" stroke="var(--color-gold)" strokeWidth="1.1" fill="none" opacity="0.55" />
            <circle cx="12" cy="12" r="1.4" fill="var(--color-gold)" />
          </svg>
          <h1 className="text-2xl">{t.login.title}</h1>
          <p className="text-sm text-[var(--color-text-secondary)]">{t.login.subtitle}</p>
        </div>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={t.login.placeholder}
          autoFocus
          className="bg-[var(--color-panel)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-[var(--color-gold)]"
        />
        {error && <p className="text-sm text-[var(--color-warning)]">{error}</p>}
        <button
          type="submit"
          className="bg-[var(--color-gold)] text-[#241505] font-semibold rounded-lg py-2.5 text-sm"
        >
          {t.login.submit}
        </button>
      </form>
    </div>
  )
}

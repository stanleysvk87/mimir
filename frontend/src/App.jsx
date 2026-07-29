import { useEffect, useState } from 'react'
import { Routes, Route, Navigate, NavLink } from 'react-router-dom'
import { api } from './lib/api.js'
import { useI18n } from './i18n/I18nContext.jsx'
import Login from './pages/Login.jsx'
import Timeline from './pages/Timeline.jsx'
import Search from './pages/Search.jsx'
import Projects from './pages/Projects.jsx'
import Threads from './pages/Threads.jsx'
import Recall from './pages/Recall.jsx'

function RequireAuth({ children }) {
  const [state, setState] = useState('checking') // checking | ok | out

  useEffect(() => {
    api.listDays().then(
      () => setState('ok'),
      (err) => setState(err.status === 401 ? 'out' : 'ok'),
    )
  }, [])

  if (state === 'checking') return null
  if (state === 'out') return <Navigate to="/login" replace />
  return children
}

function NavItem({ to, end, children }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `px-2.5 py-2 rounded-lg text-sm ${isActive ? 'text-[var(--color-text-primary)] bg-[var(--color-gold)]/10 border border-[var(--color-gold)]/25' : 'text-[var(--color-text-secondary)] hover:bg-white/5'}`
      }
    >
      {children}
    </NavLink>
  )
}

function Shell({ children }) {
  const { t, lang, setLang } = useI18n()
  return (
    <div className="min-h-screen flex">
      <aside className="w-56 border-r border-[var(--color-border)] p-5 flex flex-col gap-8 flex-none sticky top-0 h-screen overflow-y-auto">
        <div className="flex items-center gap-2.5">
          <svg viewBox="0 0 24 24" className="w-6 h-6 flex-none">
            <circle cx="12" cy="12" r="9.25" stroke="var(--color-gold)" strokeWidth="1.3" fill="none" />
            <circle cx="12" cy="12" r="4.5" stroke="var(--color-gold)" strokeWidth="1.1" fill="none" opacity="0.55" />
            <circle cx="12" cy="12" r="1.4" fill="var(--color-gold)" />
          </svg>
          <span className="font-[family-name:var(--font-display)] text-2xl">{t.appName}</span>
        </div>
        <nav className="flex flex-col gap-1">
          <NavItem to="/" end>{t.nav.timeline}</NavItem>
          <NavItem to="/search">{t.nav.search}</NavItem>
          <NavItem to="/projects">{t.nav.projects}</NavItem>
          <NavItem to="/threads">{t.nav.threads}</NavItem>
          <NavItem to="/recall">{t.nav.recall}</NavItem>
        </nav>
        <div className="mt-auto flex gap-1 text-xs text-[var(--color-text-tertiary)]">
          <button
            className={`px-2 py-1 rounded ${lang === 'en' ? 'bg-white/10 text-[var(--color-text-primary)]' : ''}`}
            onClick={() => setLang('en')}
          >
            EN
          </button>
          <button
            className={`px-2 py-1 rounded ${lang === 'sk' ? 'bg-white/10 text-[var(--color-text-primary)]' : ''}`}
            onClick={() => setLang('sk')}
          >
            SK
          </button>
        </div>
      </aside>
      <main className="flex-1 min-w-0">{children}</main>
    </div>
  )
}

function Protected({ children }) {
  return (
    <RequireAuth>
      <Shell>{children}</Shell>
    </RequireAuth>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Protected><Timeline /></Protected>} />
      <Route path="/search" element={<Protected><Search /></Protected>} />
      <Route path="/projects" element={<Protected><Projects /></Protected>} />
      <Route path="/threads" element={<Protected><Threads /></Protected>} />
      <Route path="/recall" element={<Protected><Recall /></Protected>} />
    </Routes>
  )
}

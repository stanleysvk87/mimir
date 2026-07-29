import { createContext, useContext, useMemo, useState } from 'react'
import en from './en.js'
import sk from './sk.js'

const DICTS = { en, sk }
const STORAGE_KEY = 'mimir_lang'

const I18nContext = createContext(null)

function detectDefault() {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored && DICTS[stored]) return stored
  // Default is English (portability goal) -- Slovak is an explicit
  // opt-in toggle, not autodetected from the browser locale.
  return 'en'
}

export function I18nProvider({ children }) {
  const [lang, setLang] = useState(detectDefault)

  const value = useMemo(() => {
    const dict = DICTS[lang]
    return {
      lang,
      setLang: (l) => {
        localStorage.setItem(STORAGE_KEY, l)
        setLang(l)
      },
      t: dict,
    }
  }, [lang])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used inside I18nProvider')
  return ctx
}

import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import { translations, type Language, type TranslationKey } from '@/data/translations'

const LANGUAGE_STORAGE_KEY = 'fg:language'

function resolveInitialLanguage(): Language {
  if (typeof window === 'undefined') return 'es'

  const persisted = window.localStorage.getItem(LANGUAGE_STORAGE_KEY)
  if (persisted === 'es' || persisted === 'en') return persisted

  return 'es'
}

interface I18nContextType {
  language: Language
  setLanguage: (lang: Language) => void
  t: (key: TranslationKey) => string
}

const I18nContext = createContext<I18nContextType | undefined>(undefined)

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(resolveInitialLanguage)

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language)
  }, [language])

  const t = useCallback(
    (key: TranslationKey): string => {
      return translations[language][key] || key
    },
    [language]
  )

  return (
    <I18nContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useI18n() {
  const context = useContext(I18nContext)
  if (context === undefined) {
    throw new Error('useI18n must be used within an I18nProvider')
  }
  return context
}

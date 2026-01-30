import type { ReactNode } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { ThemeProvider } from '@/components/theme-provider'
import { Footer } from '@/components/layout/footer'
import { Navbar } from '@/components/layout/navbar'
import { AuthProvider } from '@/context/AuthContext'
import { I18nProvider } from '@/context/LanguageContext'
import AuditPage from '@/pages/Audit'
import CertificatesPage from '@/pages/Certificates'
import CitizenReportPage from '@/pages/CitizenReport'
import FireDetailPage from '@/pages/FireDetail'
import HomePage from '@/pages/Home'
import LoginPage from '@/pages/Login'
import MapPage from '@/pages/MapPage'
import NotFoundPage from '@/pages/NotFound'
import SheltersPage from '@/pages/Shelters'

function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1 pt-0 pb-16 md:pt-16 md:pb-0">{children}</main>
      <Footer />
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <I18nProvider>
        <AuthProvider>
          <BrowserRouter>
            <AppShell>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/map" element={<MapPage />} />
                <Route path="/audit" element={<AuditPage />} />
                <Route path="/certificates" element={<CertificatesPage />} />
                <Route path="/citizen-report" element={<CitizenReportPage />} />
                <Route path="/fires/:id" element={<FireDetailPage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/shelters" element={<SheltersPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </AppShell>
          </BrowserRouter>
        </AuthProvider>
      </I18nProvider>
    </ThemeProvider>
  )
}

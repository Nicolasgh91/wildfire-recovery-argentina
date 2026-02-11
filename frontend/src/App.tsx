import { Suspense, lazy, type ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { ThemeProvider } from '@/components/theme-provider'
import { Footer } from '@/components/layout/footer'
import { Navbar } from '@/components/layout/navbar'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { AuthProvider } from '@/context/AuthContext'
import { I18nProvider } from '@/context/LanguageContext'
import { isFeatureEnabled } from '@/lib/featureFlags'

const HomePage = lazy(() => import('@/pages/Home'))
const MapPage = lazy(() => import('@/pages/MapPage'))
const AuditPage = lazy(() => import('@/pages/Audit'))
const CreditsPage = lazy(() => import('@/pages/Credits'))
const ExplorationPage = lazy(() => import('@/pages/Exploration'))
const ProfilePage = lazy(() => import('@/pages/Profile'))
const RegisterPage = lazy(() => import('@/pages/Register'))
const PaymentReturnPage = lazy(() => import('@/pages/PaymentReturnPage'))
const CertificatesPage = lazy(() => import('@/pages/Certificates'))
const CitizenReportPage = lazy(() => import('@/pages/CitizenReport'))
const FireHistoryPage = lazy(() => import('@/pages/FireHistory'))
const FireDetailPage = lazy(() => import('@/pages/FireDetail'))
const LoginPage = lazy(() => import('@/pages/Login'))
const SheltersPage = lazy(() => import('@/pages/Shelters'))
const FaqPage = lazy(() => import('@/pages/faq'))
const ManualPage = lazy(() => import('@/pages/manual'))
const GlossaryPage = lazy(() => import('@/pages/glossary'))
const ContactPage = lazy(() => import('@/pages/contact'))
const NotFoundPage = lazy(() => import('@/pages/NotFound'))

function AppLoading() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center gap-2 text-muted-foreground">
      <Loader2 className="h-5 w-5 animate-spin" />
      <span className="text-sm">Loading...</span>
    </div>
  )
}

function AppShell({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const isMapPage = pathname === '/map'
  const hideChrome = pathname === '/login' || pathname === '/register'
  const shellClass = isMapPage ? 'flex h-screen flex-col' : 'flex min-h-screen flex-col'
  const mainClass = hideChrome
    ? 'flex-1'
    : isMapPage
      ? 'flex-1 overflow-hidden pt-0 pb-24 md:pt-24 md:pb-0'
      : 'flex-1 pt-0 pb-24 md:pt-24 md:pb-0'

  return (
    <div className={shellClass}>
      {!hideChrome && <Navbar />}
      <main className={mainClass}>{children}</main>
      {!hideChrome && <Footer />}
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
              <Suspense fallback={<AppLoading />}>
                <Routes>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/map" element={<MapPage />} />
                  <Route
                    path="/audit"
                    element={
                      <ProtectedRoute>
                        <AuditPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/credits"
                    element={
                      <ProtectedRoute>
                        <CreditsPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/exploracion"
                    element={<ExplorationPage />}
                  />
                  <Route path="/reports" element={<Navigate to="/exploracion" replace />} />
                  <Route
                    path="/profile"
                    element={
                      <ProtectedRoute>
                        <ProfilePage />
                      </ProtectedRoute>
                    }
                  />
                  <Route path="/payments/return" element={<PaymentReturnPage />} />
                  <Route
                    path="/certificates"
                    element={isFeatureEnabled('certificates') ? <CertificatesPage /> : <NotFoundPage />}
                  />
                  <Route path="/citizen-report" element={<CitizenReportPage />} />
                  <Route path="/fires" element={<Navigate to="/fires/history" replace />} />
                  <Route
                    path="/fires/history"
                    element={
                      <ProtectedRoute>
                        <FireHistoryPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/fires/:id"
                    element={
                      <ProtectedRoute>
                        <FireDetailPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/register" element={<RegisterPage />} />
                  <Route
                    path="/shelters"
                    element={isFeatureEnabled('refuges') ? <SheltersPage /> : <NotFoundPage />}
                  />
                  <Route path="/faq" element={<FaqPage />} />
                  <Route path="/manual" element={<ManualPage />} />
                  <Route path="/glossary" element={<GlossaryPage />} />
                  <Route path="/contact" element={<ContactPage />} />
                  <Route path="*" element={<NotFoundPage />} />
                </Routes>
              </Suspense>
            </AppShell>
          </BrowserRouter>
        </AuthProvider>
      </I18nProvider>
    </ThemeProvider>
  )
}

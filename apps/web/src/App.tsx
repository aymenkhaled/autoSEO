import { BrowserRouter, Routes, Route, Navigate } from 'react-router'
import { useAuth } from '@/hooks/use-auth'
import DashboardLayout from '@/components/layout/DashboardLayout'
import LandingPage from '@/pages/LandingPage'
import LoginPage from '@/pages/LoginPage'
import SignupPage from '@/pages/SignupPage'
import PrivacyPage from '@/pages/PrivacyPage'
import TermsPage from '@/pages/TermsPage'
import DashboardPage from '@/pages/DashboardPage'
import SitesPage from '@/pages/SitesPage'
import SiteDetailPage from '@/pages/SiteDetailPage'
import IssuesPage from '@/pages/IssuesPage'
import FixesPage from '@/pages/FixesPage'
import SettingsPage from '@/pages/SettingsPage'
import AnalyticsPage from '@/pages/AnalyticsPage'
import KeywordsPage from '@/pages/KeywordsPage'
import CompetitorsPage from '@/pages/CompetitorsPage'
import TeamPage from '@/pages/TeamPage'
import ApiKeysPage from '@/pages/ApiKeysPage'
import ReportsPage from '@/pages/ReportsPage'
import BillingPage from '@/pages/BillingPage'
import IntegrationsPage from '@/pages/IntegrationsPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { loading, isAuthenticated } = useAuth()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="w-12 h-12 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-6 h-6 rounded-full bg-primary/20 animate-pulse" />
            </div>
          </div>
          <p className="text-sm font-medium text-muted-foreground">Loading AutoSEO…</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function DashboardRoute({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <DashboardLayout>{children}</DashboardLayout>
    </ProtectedRoute>
  )
}

function PublicOnlyRoute({ children }: { children: React.ReactNode }) {
  const { loading, isAuthenticated } = useAuth()
  if (loading) return null
  if (isAuthenticated) return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/login" element={<PublicOnlyRoute><LoginPage /></PublicOnlyRoute>} />
        <Route path="/signup" element={<PublicOnlyRoute><SignupPage /></PublicOnlyRoute>} />

        {/* Dashboard */}
        <Route path="/dashboard" element={<DashboardRoute><DashboardPage /></DashboardRoute>} />
        <Route path="/dashboard/sites" element={<DashboardRoute><SitesPage /></DashboardRoute>} />
        <Route path="/dashboard/sites/:id" element={<DashboardRoute><SiteDetailPage /></DashboardRoute>} />
        <Route path="/dashboard/issues" element={<DashboardRoute><IssuesPage /></DashboardRoute>} />
        <Route path="/dashboard/fixes" element={<DashboardRoute><FixesPage /></DashboardRoute>} />
        <Route path="/dashboard/analytics" element={<DashboardRoute><AnalyticsPage /></DashboardRoute>} />
        <Route path="/dashboard/keywords" element={<DashboardRoute><KeywordsPage /></DashboardRoute>} />
        <Route path="/dashboard/competitors" element={<DashboardRoute><CompetitorsPage /></DashboardRoute>} />
        <Route path="/dashboard/reports" element={<DashboardRoute><ReportsPage /></DashboardRoute>} />
        <Route path="/dashboard/team" element={<DashboardRoute><TeamPage /></DashboardRoute>} />
        <Route path="/dashboard/api-keys" element={<DashboardRoute><ApiKeysPage /></DashboardRoute>} />
        <Route path="/dashboard/billing" element={<DashboardRoute><BillingPage /></DashboardRoute>} />
        <Route path="/dashboard/settings" element={<DashboardRoute><SettingsPage /></DashboardRoute>} />
        <Route path="/dashboard/integrations" element={<DashboardRoute><IntegrationsPage /></DashboardRoute>} />

        {/* Legacy redirects */}
        <Route path="/sites" element={<Navigate to="/dashboard/sites" replace />} />
        <Route path="/issues" element={<Navigate to="/dashboard/issues" replace />} />
        <Route path="/fixes" element={<Navigate to="/dashboard/fixes" replace />} />
        <Route path="/settings" element={<Navigate to="/dashboard/settings" replace />} />
        <Route path="/reports" element={<Navigate to="/dashboard/reports" replace />} />

        {/* 404 */}
        <Route path="*" element={
          <div className="flex items-center justify-center h-screen bg-background">
            <div className="text-center">
              <h1 className="text-8xl font-black bg-gradient-to-r from-cyan-400 to-blue-600 bg-clip-text text-transparent mb-4">404</h1>
              <p className="text-lg text-muted-foreground mb-6">Page not found</p>
              <a href="/"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white bg-primary hover:bg-primary/90 transition-colors">
                Go Home
              </a>
            </div>
          </div>
        } />
      </Routes>
    </BrowserRouter>
  )
}

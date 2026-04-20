import { Link } from 'react-router'
import { Zap, Shield } from 'lucide-react'

export default function PrivacyPage() {
  const updated = 'January 1, 2025'

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border sticky top-0 bg-background/80 backdrop-blur-sm z-10">
        <div className="max-w-4xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <span className="font-bold text-foreground">AutoSEO</span>
          </Link>
          <Link to="/login" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Sign in →
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-16">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/10 flex items-center justify-center">
            <Shield className="h-5 w-5 text-cyan-500" />
          </div>
          <div>
            <h1 className="text-4xl font-bold tracking-tight text-foreground">Privacy Policy</h1>
            <p className="text-sm text-muted-foreground mt-1">Last updated: {updated}</p>
          </div>
        </div>

        <div className="prose prose-sm dark:prose-invert max-w-none space-y-8 text-foreground">
          {[
            {
              title: '1. Information We Collect',
              content: `We collect information you provide directly to us when you create an account, add a website, or communicate with us. This includes your name, email address, and payment information. We also collect information about how you use AutoSEO, including pages visited, crawls initiated, and fixes applied. When you connect a CMS integration, we collect the minimum credentials required to read and write SEO data.`,
            },
            {
              title: '2. How We Use Your Information',
              content: `We use the information we collect to provide, maintain, and improve our services, process transactions, send you technical notices and updates, respond to your comments and questions, and monitor and analyze usage patterns. We use website data you connect exclusively to perform SEO analysis and apply fixes you approve. We never sell your data to third parties.`,
            },
            {
              title: '3. Data Storage and Security',
              content: `Your data is stored in Supabase-hosted PostgreSQL databases in the EU West region. CMS credentials (API keys, OAuth tokens) are encrypted at rest using AES-256 encryption before storage. We use TLS 1.3 for all data in transit. Access to production systems is restricted to authorized personnel only and logged via our audit trail.`,
            },
            {
              title: '4. Cookies and Tracking',
              content: `We use essential cookies to maintain your session and authentication state. We do not use third-party advertising cookies or sell data for ad targeting. We use privacy-friendly analytics (no cross-site tracking) to understand how our product is used. You may opt out of analytics by contacting us.`,
            },
            {
              title: '5. Data Retention',
              content: `We retain your account data for as long as your account is active. Website crawl data is retained for 12 months by default and can be configured in Settings. After account deletion, we delete all personal data within 30 days. Aggregated, anonymized analytics data may be retained indefinitely.`,
            },
            {
              title: '6. GDPR Rights (EU Users)',
              content: `If you are located in the European Union, you have the right to access, correct, or delete your personal data. You may request a full data export at any time from Settings → Account → Export My Data. To exercise your right to erasure, delete your account in Settings → Danger Zone or email privacy@autoseo.com. We process EU personal data under the legal basis of contract performance and legitimate interests.`,
            },
            {
              title: '7. CCPA Rights (California Users)',
              content: `California residents may request disclosure of personal information we collect, use, disclose, and sell. You have the right to opt out of the sale of your personal information. We do not sell personal information. To exercise your rights, contact privacy@autoseo.com.`,
            },
            {
              title: '8. Third-Party Services',
              content: `AutoSEO integrates with third-party services including Stripe (payments), Supabase (authentication and database), and optionally your CMS platform. Each of these services has their own privacy policies. We share only the minimum data necessary for each integration to function.`,
            },
            {
              title: '9. Changes to This Policy',
              content: `We may update this Privacy Policy periodically. We will notify you of significant changes via email or a prominent notice in the application at least 30 days before they take effect. Your continued use of AutoSEO after changes take effect constitutes acceptance of the updated policy.`,
            },
            {
              title: '10. Contact',
              content: `For privacy questions or to exercise your rights, contact us at privacy@autoseo.com. For general support, use the in-app chat or email support@autoseo.com.`,
            },
          ].map((section) => (
            <section key={section.title} className="border-b border-border pb-8 last:border-0">
              <h2 className="text-lg font-semibold text-foreground mb-3">{section.title}</h2>
              <p className="text-sm text-muted-foreground leading-relaxed">{section.content}</p>
            </section>
          ))}
        </div>
      </main>

      <footer className="border-t border-border mt-16">
        <div className="max-w-4xl mx-auto px-6 py-8 flex items-center justify-between text-xs text-muted-foreground">
          <span>© {new Date().getFullYear()} AutoSEO. All rights reserved.</span>
          <div className="flex items-center gap-4">
            <Link to="/terms" className="hover:text-foreground transition-colors">Terms of Service</Link>
            <Link to="/privacy" className="hover:text-foreground transition-colors">Privacy Policy</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}

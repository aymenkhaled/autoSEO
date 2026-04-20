import { Link } from 'react-router'
import { Zap, FileText } from 'lucide-react'

export default function TermsPage() {
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
            <FileText className="h-5 w-5 text-cyan-500" />
          </div>
          <div>
            <h1 className="text-4xl font-bold tracking-tight text-foreground">Terms of Service</h1>
            <p className="text-sm text-muted-foreground mt-1">Last updated: {updated}</p>
          </div>
        </div>

        <div className="space-y-8 text-foreground">
          {[
            {
              title: '1. Acceptance of Terms',
              content: `By accessing or using AutoSEO, you agree to be bound by these Terms of Service and our Privacy Policy. If you are using AutoSEO on behalf of an organization, you are agreeing to these terms for that organization and representing that you have the authority to do so. If you do not agree to these terms, do not use AutoSEO.`,
            },
            {
              title: '2. Description of Service',
              content: `AutoSEO is an autonomous SEO platform that crawls websites, detects SEO issues, and applies fixes via CMS integrations. The service includes web crawling, AI-powered analysis using third-party APIs, issue tracking, fix application, reporting, and team collaboration features. Features available to you depend on your subscription plan.`,
            },
            {
              title: '3. Account Registration',
              content: `You must create an account to use AutoSEO. You are responsible for maintaining the security of your account credentials and for all activities that occur under your account. You must immediately notify us of any unauthorized access to your account. You must be at least 16 years old to use AutoSEO.`,
            },
            {
              title: '4. Acceptable Use',
              content: `You agree not to use AutoSEO to crawl websites you do not own or have explicit permission to crawl. You agree not to use AutoSEO to engage in illegal activities, violate others' intellectual property rights, send spam, or overload servers. We reserve the right to suspend accounts that violate these terms. You are responsible for ensuring your use of AutoSEO complies with applicable laws.`,
            },
            {
              title: '5. CMS Integration and Data Access',
              content: `When you connect a CMS integration, you grant AutoSEO limited access to read and write SEO-related data. AutoSEO will only write changes that you explicitly approve. We implement read-only tests before requesting write access. You can revoke access at any time from the Integrations page or your CMS settings. We do not access your CMS data for any purpose other than providing the AutoSEO service.`,
            },
            {
              title: '6. Subscription and Billing',
              content: `AutoSEO is offered on a subscription basis. Fees are charged in advance on a monthly or annual basis. All fees are non-refundable except where required by law. We may change our pricing with 30 days notice. If you do not agree to a price change, you may cancel before the new pricing takes effect. Overages on metered features (pages crawled, AI fixes) are billed at the end of each billing period.`,
            },
            {
              title: '7. Free Trial',
              content: `New accounts receive a 14-day free trial of the Pro plan. No credit card is required during the trial. After the trial, your account reverts to the Free plan unless you subscribe. Trial features and limits are identical to the paid Pro plan. We reserve the right to end or modify trial terms.`,
            },
            {
              title: '8. Intellectual Property',
              content: `AutoSEO and its logos, designs, and software are owned by AutoSEO and protected by intellectual property laws. We grant you a limited, non-exclusive, non-transferable license to use AutoSEO for your internal business purposes. You retain ownership of all content you provide and all data generated about your websites.`,
            },
            {
              title: '9. Disclaimer of Warranties',
              content: `AutoSEO is provided "as is" and "as available" without warranties of any kind. We do not guarantee that AutoSEO will be uninterrupted, error-free, or that AI-generated fixes will improve your SEO rankings. SEO results depend on many factors outside our control, including search engine algorithm changes. Use AI-generated fixes at your own discretion.`,
            },
            {
              title: '10. Limitation of Liability',
              content: `To the maximum extent permitted by law, AutoSEO shall not be liable for indirect, incidental, special, consequential, or punitive damages arising from your use of the service. Our total liability to you for any claims arising from your use of AutoSEO shall not exceed the amount you paid us in the 12 months preceding the claim.`,
            },
            {
              title: '11. Termination',
              content: `Either party may terminate this agreement at any time. You may cancel your subscription from the Billing page. We may suspend or terminate your account for violations of these terms. Upon termination, your right to use AutoSEO ceases immediately. We will make your data available for export for 30 days after termination.`,
            },
            {
              title: '12. Changes to Terms',
              content: `We may modify these terms at any time. We will provide at least 30 days notice of material changes via email and in-app notification. Your continued use of AutoSEO after changes take effect constitutes acceptance of the updated terms.`,
            },
            {
              title: '13. Governing Law',
              content: `These terms are governed by the laws of the State of Delaware, USA, without regard to conflict of law principles. Any disputes arising from these terms shall be resolved through binding arbitration in accordance with the American Arbitration Association rules, except that either party may seek injunctive relief in any court of competent jurisdiction.`,
            },
            {
              title: '14. Contact',
              content: `For questions about these Terms, contact legal@autoseo.com. For account or billing questions, contact support@autoseo.com.`,
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

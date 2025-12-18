import Link from 'next/link'
import { Shield, ArrowLeft } from 'lucide-react'

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-900 to-black">
      {/* Header */}
      <header className="border-b border-gray-800">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center space-x-2">
            <Shield className="w-8 h-8 text-purple-500" />
            <span className="text-xl font-bold text-white">ActorHub.ai</span>
          </Link>
          <Link href="/" className="flex items-center text-gray-400 hover:text-white transition">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Home
          </Link>
        </div>
      </header>

      {/* Content */}
      <main className="py-16">
        <div className="container mx-auto px-4 max-w-4xl">
          <h1 className="text-4xl font-bold text-white mb-8">Terms of Service</h1>
          <div className="prose prose-invert prose-lg max-w-none">
            <p className="text-gray-300 mb-6">
              Last updated: December 2024
            </p>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">1. Acceptance of Terms</h2>
              <p className="text-gray-400">
                By accessing or using ActorHub.ai, you agree to be bound by these Terms of Service. 
                If you do not agree to these terms, please do not use our services.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">2. Description of Services</h2>
              <p className="text-gray-400">
                ActorHub.ai provides a digital identity protection and monetization platform that allows 
                users to register their likeness, detect unauthorized use, and license their digital identity.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">3. User Accounts</h2>
              <ul className="list-disc list-inside text-gray-400 space-y-2">
                <li>You must provide accurate and complete information when creating an account</li>
                <li>You are responsible for maintaining the security of your account</li>
                <li>You must be at least 18 years old to use our services</li>
                <li>You may not use another person's identity without authorization</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">4. Identity Registration</h2>
              <p className="text-gray-400">
                When registering your identity, you confirm that you have the legal right to do so. 
                You may only register your own likeness or that of individuals who have given explicit consent.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">5. Marketplace and Licensing</h2>
              <ul className="list-disc list-inside text-gray-400 space-y-2">
                <li>Sellers receive 70-85% of licensing fees depending on their plan</li>
                <li>ActorHub.ai retains a platform fee of 15-30%</li>
                <li>All transactions are processed securely through Stripe</li>
                <li>Refunds are subject to our refund policy</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">6. Prohibited Uses</h2>
              <ul className="list-disc list-inside text-gray-400 space-y-2">
                <li>Creating deepfakes without proper licensing</li>
                <li>Harassment or impersonation</li>
                <li>Illegal activities</li>
                <li>Violating intellectual property rights</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">7. Limitation of Liability</h2>
              <p className="text-gray-400">
                ActorHub.ai is not liable for any indirect, incidental, or consequential damages 
                arising from your use of our services.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">8. Contact</h2>
              <p className="text-gray-400">
                For questions about these Terms, contact us at:
                <br />
                Email: legal@actorhub.ai
              </p>
            </section>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-8">
        <div className="container mx-auto px-4 text-center text-gray-500">
          <p>&copy; 2024 ActorHub.ai. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}

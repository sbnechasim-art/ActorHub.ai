import Link from 'next/link'
import { Shield, ArrowLeft } from 'lucide-react'

export default function PrivacyPage() {
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
          <h1 className="text-4xl font-bold text-white mb-8">Privacy Policy</h1>
          <div className="prose prose-invert prose-lg max-w-none">
            <p className="text-gray-300 mb-6">
              Last updated: December 2024
            </p>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">1. Introduction</h2>
              <p className="text-gray-400">
                ActorHub.ai ("we", "our", or "us") is committed to protecting your privacy. 
                This Privacy Policy explains how we collect, use, disclose, and safeguard your 
                information when you use our digital identity protection platform.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">2. Information We Collect</h2>
              <h3 className="text-xl font-medium text-white mb-2">Personal Information</h3>
              <ul className="list-disc list-inside text-gray-400 space-y-2">
                <li>Name and contact information</li>
                <li>Account credentials</li>
                <li>Payment information (processed securely via Stripe)</li>
                <li>Biometric data (facial features for identity verification)</li>
              </ul>
              <h3 className="text-xl font-medium text-white mb-2 mt-4">Usage Information</h3>
              <ul className="list-disc list-inside text-gray-400 space-y-2">
                <li>Log data and device information</li>
                <li>Usage patterns and preferences</li>
                <li>IP address and location data</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">3. How We Use Your Information</h2>
              <ul className="list-disc list-inside text-gray-400 space-y-2">
                <li>To provide and maintain our services</li>
                <li>To detect unauthorized use of your digital identity</li>
                <li>To process transactions and payments</li>
                <li>To communicate with you about our services</li>
                <li>To improve our platform and user experience</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">4. Data Security</h2>
              <p className="text-gray-400">
                We implement bank-grade encryption and security measures to protect your data. 
                Your biometric data is stored as encrypted mathematical signatures and is never 
                shared in raw form.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">5. Your Rights</h2>
              <p className="text-gray-400">
                You have the right to access, correct, or delete your personal information. 
                Contact us at privacy@actorhub.ai to exercise these rights.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-white mb-4">6. Contact Us</h2>
              <p className="text-gray-400">
                If you have questions about this Privacy Policy, please contact us at:
                <br />
                Email: privacy@actorhub.ai
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

'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Shield, Check, ArrowRight } from 'lucide-react'

export default function PricingPage() {
  const plans = [
    {
      name: 'Free',
      price: '$0',
      period: 'forever',
      description: 'Basic protection for individuals',
      features: [
        'Basic identity registration',
        '10 verifications/month',
        'Email notifications',
        'Community support',
      ],
      cta: 'Get Started',
      popular: false,
    },
    {
      name: 'Pro',
      price: '$29',
      period: '/month',
      description: 'Full protection and monetization',
      features: [
        'Everything in Free',
        'Unlimited verifications',
        'Real-time alerts',
        'Marketplace listing',
        'Actor Pack creation',
        'Revenue analytics',
        'Priority support',
        'API access (1,000 calls/month)',
      ],
      cta: 'Start Free Trial',
      popular: true,
    },
    {
      name: 'Enterprise',
      price: 'Custom',
      period: '',
      description: 'For agencies and studios',
      features: [
        'Everything in Pro',
        'Unlimited identities',
        'Unlimited API calls',
        'White-label options',
        'Custom integrations',
        'Dedicated account manager',
        'Legal support',
        'SLA guarantee',
      ],
      cta: 'Contact Sales',
      popular: false,
    },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-900 to-black">
      {/* Header */}
      <header className="border-b border-gray-800">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center space-x-2">
            <Shield className="w-8 h-8 text-purple-500" />
            <span className="text-xl font-bold text-white">ActorHub.ai</span>
          </Link>
          <nav className="flex items-center space-x-6">
            <Link href="/marketplace" className="text-gray-300 hover:text-white">
              Marketplace
            </Link>
            <Link href="/developers" className="text-gray-300 hover:text-white">
              Developers
            </Link>
            <Link href="/pricing" className="text-purple-400">
              Pricing
            </Link>
            <Link href="/sign-in">
              <Button variant="outline" className="border-gray-700 text-gray-300">
                Sign In
              </Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="py-20 text-center">
        <div className="container mx-auto px-4">
          <h1 className="text-5xl font-bold text-white mb-6">
            Simple, Transparent Pricing
          </h1>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Choose the plan that fits your needs. All plans include our core identity protection features.
          </p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="pb-20">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {plans.map((plan, index) => (
              <Card
                key={index}
                className={`relative bg-gray-800/50 border-gray-700 ${
                  plan.popular ? 'border-purple-500 scale-105' : ''
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <span className="bg-purple-600 text-white text-sm px-4 py-1 rounded-full">
                      Most Popular
                    </span>
                  </div>
                )}
                <CardHeader className="text-center pt-8">
                  <CardTitle className="text-white text-2xl">{plan.name}</CardTitle>
                  <div className="mt-4">
                    <span className="text-4xl font-bold text-white">{plan.price}</span>
                    <span className="text-gray-400">{plan.period}</span>
                  </div>
                  <CardDescription className="text-gray-400 mt-2">
                    {plan.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-6">
                  <ul className="space-y-4 mb-8">
                    {plan.features.map((feature, featureIndex) => (
                      <li key={featureIndex} className="flex items-center text-gray-300">
                        <Check className="w-5 h-5 text-green-400 mr-3 flex-shrink-0" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <Link href="/sign-up">
                    <Button
                      className={`w-full ${
                        plan.popular
                          ? 'bg-purple-600 hover:bg-purple-700'
                          : 'bg-gray-700 hover:bg-gray-600'
                      }`}
                    >
                      {plan.cta}
                      <ArrowRight className="w-4 h-4 ml-2" />
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-20 border-t border-gray-800">
        <div className="container mx-auto px-4 max-w-4xl">
          <h2 className="text-3xl font-bold text-white text-center mb-12">
            Frequently Asked Questions
          </h2>
          <div className="space-y-6">
            {[
              {
                q: 'What happens when someone uses my likeness without permission?',
                a: 'Our system detects unauthorized usage and alerts you immediately. You can then choose to request takedown, pursue licensing fees, or take legal action with our support.',
              },
              {
                q: 'How does monetization work?',
                a: 'When a company wants to use your likeness in AI-generated content, they pay a licensing fee. You receive 70-85% of the fee depending on your plan.',
              },
              {
                q: 'Can I upgrade or downgrade my plan anytime?',
                a: 'Yes, you can change your plan at any time. Upgrades are effective immediately, and downgrades take effect at the end of your billing cycle.',
              },
              {
                q: 'Is my biometric data secure?',
                a: 'We use bank-grade encryption and never share your raw biometric data. Only encrypted signatures are used for matching.',
              },
            ].map((faq, index) => (
              <div key={index} className="bg-gray-800/30 rounded-lg p-6">
                <h3 className="text-white font-semibold mb-2">{faq.q}</h3>
                <p className="text-gray-400">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-8">
        <div className="container mx-auto px-4 text-center text-gray-500">
          <p>&copy; 2024 ActorHub.ai. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}

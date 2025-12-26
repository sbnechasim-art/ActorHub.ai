'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Logo } from '@/components/ui/logo'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import {
  Check, X, Zap, Shield, Crown, Building2,
  ArrowRight, HelpCircle, Star, Loader2
} from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'
import { subscriptionsApi } from '@/lib/api'
import { logger } from '@/lib/logger'

const BILLING_PERIODS = ['monthly', 'yearly'] as const
type BillingPeriod = typeof BILLING_PERIODS[number]

interface PricingTier {
  name: string
  planId: string // Used for Stripe checkout
  description: string
  icon: React.ElementType
  monthlyPrice: number
  yearlyPrice: number
  features: string[]
  notIncluded?: string[]
  highlighted?: boolean
  cta: string
  ctaVariant: 'default' | 'gradient' | 'outline'
}

const PRICING_TIERS: PricingTier[] = [
  {
    name: 'Free',
    planId: 'free',
    description: 'Perfect for getting started and exploring the platform',
    icon: Zap,
    monthlyPrice: 0,
    yearlyPrice: 0,
    features: [
      '1 Digital Identity',
      'Basic face protection',
      '100 verifications/month',
      'Community support',
      'Basic analytics',
    ],
    notIncluded: [
      'Commercial licensing',
      'Voice cloning',
      'Priority support',
      'Advanced analytics',
    ],
    cta: 'Get Started Free',
    ctaVariant: 'outline',
  },
  {
    name: 'Creator',
    planId: 'creator',
    description: 'For content creators ready to monetize their identity',
    icon: Shield,
    monthlyPrice: 29,
    yearlyPrice: 290,
    features: [
      '5 Digital Identities',
      'Advanced face protection',
      '5,000 verifications/month',
      'Voice cloning (basic)',
      'Marketplace listing',
      'License management',
      'Email support',
      'Analytics dashboard',
      'Custom watermarks',
    ],
    notIncluded: [
      'White-label options',
      'SLA guarantee',
    ],
    highlighted: true,
    cta: 'Start Creator Plan',
    ctaVariant: 'gradient',
  },
  {
    name: 'Professional',
    planId: 'professional',
    description: 'For serious creators and small studios',
    icon: Crown,
    monthlyPrice: 99,
    yearlyPrice: 990,
    features: [
      '25 Digital Identities',
      'Premium face protection',
      'Unlimited verifications',
      'Advanced voice cloning',
      'Motion capture support',
      'Priority marketplace placement',
      'Custom licensing terms',
      'Priority support',
      'Advanced analytics & reports',
      'API access',
      'Team members (up to 5)',
    ],
    cta: 'Go Professional',
    ctaVariant: 'default',
  },
  {
    name: 'Enterprise',
    planId: 'enterprise',
    description: 'Custom solutions for studios and large organizations',
    icon: Building2,
    monthlyPrice: -1,
    yearlyPrice: -1,
    features: [
      'Unlimited identities',
      'Enterprise-grade protection',
      'Unlimited everything',
      'Full voice & motion suite',
      'White-label options',
      'Custom integrations',
      'Dedicated account manager',
      '24/7 priority support',
      'SLA guarantee (99.9%)',
      'On-premise deployment option',
      'Custom contracts',
      'Unlimited team members',
    ],
    cta: 'Contact Sales',
    ctaVariant: 'outline',
  },
]

const FAQS = [
  {
    question: 'What is a Digital Identity?',
    answer: 'A Digital Identity is a verified representation of your face, voice, or likeness that you can protect and monetize through our platform. Each identity includes face embeddings, optional voice models, and legal protection.',
  },
  {
    question: 'How does face protection work?',
    answer: 'Our AI continuously monitors the web for unauthorized use of your likeness. When detected, we help you take action through automated DMCA notices, platform reporting, and legal support if needed.',
  },
  {
    question: 'Can I upgrade or downgrade my plan?',
    answer: 'Yes! You can change your plan at any time. When upgrading, you\'ll be charged the prorated difference. When downgrading, the new rate applies at your next billing cycle.',
  },
  {
    question: 'What payment methods do you accept?',
    answer: 'We accept all major credit cards (Visa, Mastercard, American Express), PayPal, and bank transfers for Enterprise plans. All payments are processed securely through Stripe.',
  },
  {
    question: 'Is there a refund policy?',
    answer: 'Yes, we offer a 14-day money-back guarantee for all paid plans. If you\'re not satisfied, contact our support team for a full refund within the first 14 days.',
  },
  {
    question: 'How do creator earnings work?',
    answer: 'When someone licenses your identity, you receive 80% of the license fee. Earnings have a 7-day holding period before becoming available for withdrawal. Minimum payout is $50.',
  },
]

const FEATURE_COMPARISON = [
  { feature: 'Digital Identities', free: '1', creator: '5', pro: '25', enterprise: 'Unlimited' },
  { feature: 'Monthly Verifications', free: '100', creator: '5,000', pro: 'Unlimited', enterprise: 'Unlimited' },
  { feature: 'Face Protection', free: 'Basic', creator: 'Advanced', pro: 'Premium', enterprise: 'Enterprise' },
  { feature: 'Voice Cloning', free: false, creator: 'Basic', pro: 'Advanced', enterprise: 'Full Suite' },
  { feature: 'Motion Capture', free: false, creator: false, pro: true, enterprise: true },
  { feature: 'Marketplace Listing', free: false, creator: true, pro: 'Priority', enterprise: 'Premium' },
  { feature: 'API Access', free: false, creator: 'Limited', pro: true, enterprise: 'Full' },
  { feature: 'Team Members', free: '1', creator: '1', pro: '5', enterprise: 'Unlimited' },
  { feature: 'Support', free: 'Community', creator: 'Email', pro: 'Priority', enterprise: '24/7 Dedicated' },
  { feature: 'Analytics', free: 'Basic', creator: 'Standard', pro: 'Advanced', enterprise: 'Custom' },
  { feature: 'White Label', free: false, creator: false, pro: false, enterprise: true },
  { feature: 'SLA Guarantee', free: false, creator: false, pro: false, enterprise: '99.9%' },
]

export default function PricingPage() {
  const router = useRouter()
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const [billingPeriod, setBillingPeriod] = useState<BillingPeriod>('monthly')
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null)
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Handle subscription checkout
  const handleSubscribe = async (tier: PricingTier) => {
    setError(null)

    // Free plan - just redirect to sign-up
    if (tier.planId === 'free') {
      router.push('/sign-up')
      return
    }

    // Enterprise - redirect to contact
    if (tier.planId === 'enterprise') {
      router.push('/contact')
      return
    }

    // Paid plans - require authentication
    if (!isAuthenticated) {
      // Store intended plan in session storage
      sessionStorage.setItem('intendedPlan', JSON.stringify({
        plan: tier.planId,
        interval: billingPeriod,
      }))
      router.push('/sign-in?redirect=/pricing')
      return
    }

    // Create Stripe checkout session
    try {
      setLoadingPlan(tier.planId)
      const response = await subscriptionsApi.createCheckout({
        plan: tier.planId,
        interval: billingPeriod,
      })

      if (response.url) {
        // Redirect to Stripe Checkout
        window.location.href = response.url
      } else {
        throw new Error('No checkout URL returned')
      }
    } catch (err: unknown) {
      logger.error('Subscription checkout error', err)
      const errorMessage = err instanceof Error ? err.message : 'Failed to start checkout. Please try again.'
      setError(errorMessage)
    } finally {
      setLoadingPlan(null)
    }
  }

  const getPrice = (tier: PricingTier) => {
    if (tier.monthlyPrice === -1) return 'Custom'
    const price = billingPeriod === 'monthly' ? tier.monthlyPrice : tier.yearlyPrice
    return price === 0 ? 'Free' : `$${price}`
  }

  const getPeriodLabel = (tier: PricingTier) => {
    if (tier.monthlyPrice === -1 || tier.monthlyPrice === 0) return ''
    return billingPeriod === 'monthly' ? '/month' : '/year'
  }

  const getSavings = (tier: PricingTier) => {
    if (tier.monthlyPrice <= 0) return null
    const monthlyCost = tier.monthlyPrice * 12
    const yearlyCost = tier.yearlyPrice
    const savings = monthlyCost - yearlyCost
    if (savings > 0 && billingPeriod === 'yearly') {
      return `Save $${savings}/year`
    }
    return null
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-800">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/">
            <Logo variant="auto" size="md" />
          </Link>
          <div className="hidden md:flex items-center gap-8">
            <Link href="/marketplace" className="text-slate-400 hover:text-white transition">
              Marketplace
            </Link>
            <Link href="/developers" className="text-slate-400 hover:text-white transition">
              Developers
            </Link>
            <Link href="/pricing" className="text-white font-medium">
              Pricing
            </Link>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/sign-in">
              <Button variant="ghost" className="text-slate-300">
                Sign In
              </Button>
            </Link>
            <Link href="/sign-up">
              <Button variant="gradient">Get Started</Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-16 px-4">
        <div className="container mx-auto text-center max-w-4xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <h1 className="text-4xl md:text-6xl font-bold text-white mb-6">
              Simple, Transparent{' '}
              <span className="gradient-text">Pricing</span>
            </h1>
            <p className="text-xl text-slate-400 mb-8 max-w-2xl mx-auto">
              Choose the plan that fits your needs. Protect your identity,
              monetize your likeness, and take control of your digital presence.
            </p>

            {/* Billing Toggle */}
            <div className="inline-flex items-center gap-4 p-1 rounded-full bg-slate-800/50 border border-slate-700">
              <button
                onClick={() => setBillingPeriod('monthly')}
                className={cn(
                  'px-6 py-2 rounded-full text-sm font-medium transition',
                  billingPeriod === 'monthly'
                    ? 'bg-blue-500 text-white'
                    : 'text-slate-400 hover:text-white'
                )}
              >
                Monthly
              </button>
              <button
                onClick={() => setBillingPeriod('yearly')}
                className={cn(
                  'px-6 py-2 rounded-full text-sm font-medium transition flex items-center gap-2',
                  billingPeriod === 'yearly'
                    ? 'bg-blue-500 text-white'
                    : 'text-slate-400 hover:text-white'
                )}
              >
                Yearly
                <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">
                  Save 17%
                </span>
              </button>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mt-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg max-w-md mx-auto">
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            )}
          </motion.div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="pb-20 px-4">
        <div className="container mx-auto">
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-7xl mx-auto">
            {PRICING_TIERS.map((tier, index) => (
              <motion.div
                key={tier.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card
                  className={cn(
                    'relative h-full flex flex-col',
                    tier.highlighted
                      ? 'border-blue-500 bg-gradient-to-b from-blue-500/10 to-slate-800/50'
                      : 'border-slate-700 bg-slate-800/50'
                  )}
                >
                  {tier.highlighted && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <span className="bg-blue-500 text-white text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1">
                        <Star className="w-3 h-3" /> Most Popular
                      </span>
                    </div>
                  )}

                  <CardHeader className="pb-4">
                    <div className={cn(
                      'w-12 h-12 rounded-lg flex items-center justify-center mb-4',
                      tier.highlighted ? 'bg-blue-500/20' : 'bg-slate-700'
                    )}>
                      <tier.icon className={cn(
                        'w-6 h-6',
                        tier.highlighted ? 'text-blue-400' : 'text-slate-400'
                      )} />
                    </div>
                    <CardTitle className="text-xl text-white">{tier.name}</CardTitle>
                    <CardDescription className="text-slate-400 text-sm">
                      {tier.description}
                    </CardDescription>
                  </CardHeader>

                  <CardContent className="flex-1 flex flex-col">
                    {/* Price */}
                    <div className="mb-6">
                      <div className="flex items-baseline gap-1">
                        <span className="text-4xl font-bold text-white">
                          {getPrice(tier)}
                        </span>
                        <span className="text-slate-400">
                          {getPeriodLabel(tier)}
                        </span>
                      </div>
                      {getSavings(tier) && (
                        <p className="text-green-400 text-sm mt-1">
                          {getSavings(tier)}
                        </p>
                      )}
                    </div>

                    {/* Features */}
                    <ul className="space-y-3 mb-6 flex-1">
                      {tier.features.map((feature) => (
                        <li key={feature} className="flex items-start gap-2">
                          <Check className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
                          <span className="text-sm text-slate-300">{feature}</span>
                        </li>
                      ))}
                      {tier.notIncluded?.map((feature) => (
                        <li key={feature} className="flex items-start gap-2 opacity-50">
                          <X className="w-5 h-5 text-slate-500 shrink-0 mt-0.5" />
                          <span className="text-sm text-slate-500">{feature}</span>
                        </li>
                      ))}
                    </ul>

                    {/* CTA */}
                    <Button
                      variant={tier.ctaVariant as any}
                      className="w-full"
                      size="lg"
                      onClick={() => handleSubscribe(tier)}
                      disabled={loadingPlan === tier.planId || authLoading}
                    >
                      {loadingPlan === tier.planId ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        <>
                          {tier.cta}
                          <ArrowRight className="w-4 h-4 ml-2" />
                        </>
                      )}
                    </Button>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Feature Comparison */}
      <section className="py-20 px-4 bg-slate-900/50">
        <div className="container mx-auto max-w-6xl">
          <h2 className="text-3xl font-bold text-white text-center mb-12">
            Compare All Features
          </h2>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left py-4 px-4 text-slate-400 font-medium">Feature</th>
                  <th className="text-center py-4 px-4 text-slate-400 font-medium">Free</th>
                  <th className="text-center py-4 px-4 text-blue-400 font-medium">Creator</th>
                  <th className="text-center py-4 px-4 text-slate-400 font-medium">Professional</th>
                  <th className="text-center py-4 px-4 text-slate-400 font-medium">Enterprise</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {FEATURE_COMPARISON.map((row) => (
                  <tr key={row.feature} className="border-b border-slate-800">
                    <td className="py-4 px-4 text-white">{row.feature}</td>
                    {(['free', 'creator', 'pro', 'enterprise'] as const).map((plan) => {
                      const value = row[plan]
                      return (
                        <td key={plan} className="text-center py-4 px-4">
                          {value === true ? (
                            <Check className="w-5 h-5 text-green-400 mx-auto" />
                          ) : value === false ? (
                            <X className="w-5 h-5 text-slate-600 mx-auto" />
                          ) : (
                            <span className={cn(
                              'text-sm',
                              plan === 'creator' ? 'text-blue-400' : 'text-slate-400'
                            )}>
                              {value}
                            </span>
                          )}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-20 px-4">
        <div className="container mx-auto max-w-3xl">
          <h2 className="text-3xl font-bold text-white text-center mb-4">
            Frequently Asked Questions
          </h2>
          <p className="text-slate-400 text-center mb-12">
            Everything you need to know about ActorHub pricing
          </p>

          <div className="space-y-4">
            {FAQS.map((faq, index) => (
              <Card
                key={index}
                className="border-slate-700 bg-slate-800/50 cursor-pointer overflow-hidden"
                onClick={() => setExpandedFaq(expandedFaq === index ? null : index)}
              >
                <CardContent className="p-0">
                  <div className="flex items-center justify-between p-4">
                    <h3 className="font-medium text-white flex items-center gap-2">
                      <HelpCircle className="w-5 h-5 text-blue-400" />
                      {faq.question}
                    </h3>
                    <motion.div
                      animate={{ rotate: expandedFaq === index ? 180 : 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <ArrowRight className="w-5 h-5 text-slate-400 rotate-90" />
                    </motion.div>
                  </div>
                  <motion.div
                    initial={false}
                    animate={{
                      height: expandedFaq === index ? 'auto' : 0,
                      opacity: expandedFaq === index ? 1 : 0,
                    }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <p className="px-4 pb-4 text-slate-400 text-sm">
                      {faq.answer}
                    </p>
                  </motion.div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-4">
        <div className="container mx-auto max-w-4xl text-center">
          <Card className="border-blue-500/30 bg-gradient-to-r from-blue-500/10 to-purple-500/10 p-8 md:p-12">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Ready to Protect Your Identity?
            </h2>
            <p className="text-slate-400 mb-8 max-w-2xl mx-auto">
              Join thousands of creators who trust ActorHub to protect and monetize
              their digital presence. Start free, upgrade anytime.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/sign-up">
                <Button size="xl" variant="gradient">
                  Get Started Free
                  <ArrowRight className="w-5 h-5 ml-2" />
                </Button>
              </Link>
              <Link href="/contact">
                <Button size="xl" variant="outline">
                  Talk to Sales
                </Button>
              </Link>
            </div>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-12 px-4">
        <div className="container mx-auto text-center text-slate-500 text-sm">
          <p>&copy; {new Date().getFullYear()} ActorHub.ai. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}

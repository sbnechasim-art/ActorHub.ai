'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { Button } from '@/components/ui/button'
import { Logo } from '@/components/ui/logo'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Shield, DollarSign, Zap, CheckCircle, ArrowRight, Play, X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export default function HomePage() {
  const [showDemoModal, setShowDemoModal] = useState(false)
  const modalRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  // Focus trap for demo modal
  useEffect(() => {
    if (!showDemoModal) return

    const modal = modalRef.current
    if (!modal) return

    // Get all focusable elements
    const focusableSelector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    const focusableElements = modal.querySelectorAll<HTMLElement>(focusableSelector)
    const firstFocusable = focusableElements[0]
    const lastFocusable = focusableElements[focusableElements.length - 1]

    // Focus first element when modal opens
    firstFocusable?.focus()

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowDemoModal(false)
        return
      }

      if (e.key !== 'Tab') return

      if (e.shiftKey) {
        // Shift+Tab: go backwards
        if (document.activeElement === firstFocusable) {
          e.preventDefault()
          lastFocusable?.focus()
        }
      } else {
        // Tab: go forwards
        if (document.activeElement === lastFocusable) {
          e.preventDefault()
          firstFocusable?.focus()
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [showDemoModal])

  // Return focus to trigger when modal closes
  useEffect(() => {
    if (!showDemoModal) {
      triggerRef.current?.focus()
    }
  }, [showDemoModal])

  const openDemoModal = useCallback(() => {
    setShowDemoModal(true)
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-800">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Logo variant="auto" size="md" />
          <div className="hidden md:flex items-center gap-8">
            <Link href="/marketplace" className="text-slate-400 hover:text-white transition">
              Marketplace
            </Link>
            <Link href="/developers" className="text-slate-400 hover:text-white transition">
              Developers
            </Link>
            <Link href="/pricing" className="text-slate-400 hover:text-white transition">
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

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4 relative overflow-hidden">
        {/* Background Effects */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-gradient-to-r from-purple-500/10 to-blue-500/10 rounded-full filter blur-3xl" />
        </div>

        <div className="container mx-auto text-center max-w-4xl relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            {/* Hero Logo */}
            <motion.div
              className="flex justify-center mb-8"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.6, ease: "easeOut" }}
            >
              <div className="relative w-44 h-44 md:w-56 md:h-56 drop-shadow-[0_0_35px_rgba(59,130,246,0.5)]">
                <Image
                  src="/logo.png"
                  alt="ActorHub.ai"
                  fill
                  className="object-contain"
                  priority
                />
              </div>
            </motion.div>

            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm mb-8">
              <Shield className="w-4 h-4" />
              Trusted by 10,000+ creators worldwide
            </div>

            <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight">
              Protect Your
              <span className="gradient-text"> Digital Identity</span>
            </h1>

            <p className="text-xl text-slate-400 mb-12 max-w-2xl mx-auto">
              The global platform for managing digital rights on your face and likeness.
              Stop unauthorized AI deepfakes. Monetize your identity on your terms.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/sign-up">
                <Button size="xl" variant="gradient" className="w-full sm:w-auto">
                  Protect Your Identity
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </Link>
              <Button
                ref={triggerRef}
                size="xl"
                variant="outline"
                className="w-full sm:w-auto"
                onClick={openDemoModal}
              >
                <Play className="mr-2 w-5 h-5" />
                Watch Demo
              </Button>
            </div>
          </motion.div>

          {/* Hero Stats */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="grid grid-cols-3 gap-8 mt-20 max-w-2xl mx-auto"
          >
            <div className="text-center">
              <div className="text-3xl font-bold text-white">50K+</div>
              <div className="text-slate-500">Identities Protected</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-white">$2M+</div>
              <div className="text-slate-500">Creator Earnings</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-white">99.9%</div>
              <div className="text-slate-500">Match Accuracy</div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4 bg-slate-900/50">
        <div className="container mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Complete Identity Protection Suite
            </h2>
            <p className="text-slate-400 max-w-2xl mx-auto">
              Everything you need to protect and monetize your digital likeness
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <Card className="bg-slate-800/50 border-slate-700 card-hover">
              <CardHeader>
                <div className="w-12 h-12 rounded-lg bg-blue-500/20 flex items-center justify-center mb-4">
                  <Shield className="w-6 h-6 text-blue-400" />
                </div>
                <CardTitle className="text-white">Identity Registry</CardTitle>
                <CardDescription>
                  Register your face and likeness in our global protection database
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-slate-400">
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    AI-powered face recognition
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    Real-time detection alerts
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    Legal protection support
                  </li>
                </ul>
              </CardContent>
            </Card>

            <Card className="bg-slate-800/50 border-slate-700 card-hover">
              <CardHeader>
                <div className="w-12 h-12 rounded-lg bg-purple-500/20 flex items-center justify-center mb-4">
                  <DollarSign className="w-6 h-6 text-purple-400" />
                </div>
                <CardTitle className="text-white">Marketplace</CardTitle>
                <CardDescription>
                  License your likeness for commercial AI projects
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-slate-400">
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    Set your own pricing
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    Automated licensing
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    Usage tracking & royalties
                  </li>
                </ul>
              </CardContent>
            </Card>

            <Card className="bg-slate-800/50 border-slate-700 card-hover">
              <CardHeader>
                <div className="w-12 h-12 rounded-lg bg-green-500/20 flex items-center justify-center mb-4">
                  <Zap className="w-6 h-6 text-green-400" />
                </div>
                <CardTitle className="text-white">Actor Packs</CardTitle>
                <CardDescription>
                  Create AI-ready models of yourself for licensed use
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-slate-400">
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    Face + Voice + Motion
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    High-quality generation
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    Works with major AI tools
                  </li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 px-4">
        <div className="container mx-auto max-w-4xl">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Get Protected in Minutes
            </h2>
          </div>

          <div className="space-y-8">
            {[
              {
                step: '01',
                title: 'Register Your Identity',
                description: 'Upload photos and verify your identity. Our AI creates a unique biometric signature.'
              },
              {
                step: '02',
                title: 'Set Your Preferences',
                description: 'Choose protection level, set licensing terms, and define what uses are allowed.'
              },
              {
                step: '03',
                title: 'Start Earning',
                description: 'When platforms check faces, they find you. Licensed uses generate revenue automatically.'
              }
            ].map((item, i) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="flex gap-6 items-start"
              >
                <div className="text-5xl font-bold text-slate-700">{item.step}</div>
                <div>
                  <h3 className="text-xl font-semibold text-white mb-2">{item.title}</h3>
                  <p className="text-slate-400">{item.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4">
        <div className="container mx-auto">
          <Card className="bg-gradient-to-r from-blue-600 to-purple-600 border-0 overflow-hidden relative">
            {/* Background Logo Watermark */}
            <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/4 opacity-10 pointer-events-none">
              <div className="relative w-80 h-80">
                <Image
                  src="/logo.png"
                  alt=""
                  fill
                  className="object-contain"
                  aria-hidden="true"
                />
              </div>
            </div>
            <CardContent className="p-12 text-center relative">
              <div className="absolute inset-0 bg-grid-white/10" />
              <div className="relative z-10">
                <div className="flex justify-center mb-6">
                  <div className="relative w-16 h-16">
                    <Image
                      src="/logo.png"
                      alt="ActorHub.ai"
                      fill
                      className="object-contain"
                      style={{
                        filter: 'drop-shadow(0 0 15px rgba(255, 255, 255, 0.3))',
                      }}
                    />
                  </div>
                </div>
                <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                  Ready to Protect Your Identity?
                </h2>
                <p className="text-white/80 mb-8 max-w-xl mx-auto">
                  Join thousands of creators who are taking control of their digital presence.
                </p>
                <Link href="/sign-up">
                  <Button size="xl" className="bg-white text-slate-900 hover:bg-slate-100">
                    Get Started Free
                    <ArrowRight className="ml-2 w-5 h-5" />
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-4 border-t border-slate-800">
        <div className="container mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6 mb-8">
            <Logo variant="full" size="sm" href="/" />
            <div className="text-slate-500 text-sm">
              {new Date().getFullYear()} ActorHub.ai. All rights reserved.
            </div>
            <div className="flex gap-6 text-sm text-slate-500">
              <Link href="/privacy" className="hover:text-white transition">Privacy</Link>
              <Link href="/terms" className="hover:text-white transition">Terms</Link>
              <Link href="/contact" className="hover:text-white transition">Contact</Link>
            </div>
          </div>
          {/* Owner Info */}
          <div className="border-t border-slate-800 pt-6 text-center">
            <p className="text-slate-500 text-sm mb-2">
              Created by <span className="text-white font-medium">SHILO BARDA</span>
            </p>
            <div className="flex flex-wrap justify-center gap-4 text-xs text-slate-600">
              <a href="mailto:Sbnechasim@gmail.com" className="hover:text-purple-400 transition">
                Sbnechasim@gmail.com
              </a>
              <span className="text-slate-700">|</span>
              <a href="tel:+972506805787" className="hover:text-purple-400 transition">
                +972-50-680-5787
              </a>
            </div>
          </div>
        </div>
      </footer>

      {/* Demo Video Modal */}
      <AnimatePresence>
        {showDemoModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
            onClick={() => setShowDemoModal(false)}
          >
            <motion.div
              ref={modalRef}
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="relative w-full max-w-4xl aspect-video bg-slate-900 rounded-xl overflow-hidden"
              onClick={(e) => e.stopPropagation()}
              role="dialog"
              aria-modal="true"
              aria-label="Demo video"
            >
              <button
                onClick={() => setShowDemoModal(false)}
                className="absolute top-4 right-4 z-10 p-2 rounded-full bg-slate-800/80 text-white hover:bg-slate-700 transition"
                aria-label="Close demo video"
              >
                <X className="w-5 h-5" />
              </button>
              <div className="w-full h-full flex items-center justify-center">
                <div className="text-center">
                  <div className="w-20 h-20 rounded-full bg-purple-500/20 flex items-center justify-center mx-auto mb-4">
                    <Play className="w-10 h-10 text-purple-400" />
                  </div>
                  <p className="text-white text-xl font-semibold mb-2">Demo Video Coming Soon</p>
                  <p className="text-slate-400">
                    We're preparing an awesome demo to show you how ActorHub.ai works.
                  </p>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

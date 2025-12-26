'use client'

import { useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Shield, CheckCircle, Download, ArrowRight, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useCartStore } from '@/store/cart'

function SuccessContent() {
  const searchParams = useSearchParams()
  const sessionId = searchParams.get('session_id')
  const { clearCart } = useCartStore()

  useEffect(() => {
    // Clear cart on successful payment
    clearCart()
    // Clear the pending cart from session storage
    sessionStorage.removeItem('pending_checkout_cart')
  }, [clearCart])

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-xl">
        <div className="container mx-auto px-4 h-16 flex items-center justify-center">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-white">ActorHub.ai</span>
          </Link>
        </div>
      </header>

      <main className="container mx-auto px-4 py-16">
        <div className="max-w-2xl mx-auto text-center">
          {/* Success Icon */}
          <div className="relative inline-flex mb-8">
            <div className="w-24 h-24 rounded-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
              <CheckCircle className="w-12 h-12 text-white" />
            </div>
            <div className="absolute -top-2 -right-2 w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
          </div>

          <h1 className="text-4xl font-bold text-white mb-4">
            Payment Successful!
          </h1>
          <p className="text-xl text-slate-400 mb-8">
            Thank you for your purchase. Your licenses are now active and ready to use.
          </p>

          {/* Order Details Card */}
          <Card className="bg-slate-800/50 border-slate-700 mb-8">
            <CardContent className="p-8">
              <div className="space-y-6">
                <div className="flex items-center justify-between pb-4 border-b border-slate-700">
                  <span className="text-slate-400">Status</span>
                  <span className="flex items-center gap-2 text-green-400 font-medium">
                    <CheckCircle className="w-4 h-4" />
                    Completed
                  </span>
                </div>

                {sessionId && (
                  <div className="flex items-center justify-between pb-4 border-b border-slate-700">
                    <span className="text-slate-400">Transaction ID</span>
                    <span className="text-white font-mono text-sm">
                      {sessionId.slice(0, 20)}...
                    </span>
                  </div>
                )}

                <div className="text-center pt-4">
                  <p className="text-slate-400 mb-4">
                    A confirmation email has been sent to your registered email address.
                  </p>
                  <p className="text-sm text-slate-500">
                    Your licenses will appear in your dashboard within a few minutes.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Next Steps */}
          <div className="grid md:grid-cols-2 gap-4 mb-8">
            <Card className="bg-slate-800/50 border-slate-700 hover:border-purple-500/50 transition cursor-pointer">
              <CardContent className="p-6">
                <Link href="/dashboard" className="block">
                  <div className="w-12 h-12 rounded-lg bg-purple-500/20 flex items-center justify-center mx-auto mb-4">
                    <Shield className="w-6 h-6 text-purple-400" />
                  </div>
                  <h3 className="font-semibold text-white mb-2">View Dashboard</h3>
                  <p className="text-sm text-slate-400">
                    Access your licenses and manage your identities
                  </p>
                </Link>
              </CardContent>
            </Card>

            <Card className="bg-slate-800/50 border-slate-700 hover:border-blue-500/50 transition cursor-pointer">
              <CardContent className="p-6">
                <Link href="/identity/create" className="block">
                  <div className="w-12 h-12 rounded-lg bg-blue-500/20 flex items-center justify-center mx-auto mb-4">
                    <Download className="w-6 h-6 text-blue-400" />
                  </div>
                  <h3 className="font-semibold text-white mb-2">Create Content</h3>
                  <p className="text-sm text-slate-400">
                    Start using your licensed actor packs
                  </p>
                </Link>
              </CardContent>
            </Card>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button asChild className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700">
              <Link href="/dashboard">
                Go to Dashboard
                <ArrowRight className="w-4 h-4 ml-2" />
              </Link>
            </Button>
            <Button asChild variant="outline" className="border-slate-700 text-slate-300">
              <Link href="/marketplace">
                Continue Shopping
              </Link>
            </Button>
          </div>
        </div>
      </main>
    </div>
  )
}

export default function CheckoutSuccessPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full" />
      </div>
    }>
      <SuccessContent />
    </Suspense>
  )
}

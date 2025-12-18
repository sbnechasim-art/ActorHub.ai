'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  Shield, ShoppingCart, Lock, CreditCard, ArrowLeft,
  Trash2, CheckCircle, AlertCircle, Loader2
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useCartStore } from '@/store/cart'
import { marketplaceApi } from '@/lib/api'
import { formatCurrency } from '@/lib/utils'
import { logger } from '@/lib/logger'

export default function CheckoutPage() {
  const router = useRouter()
  const { items, removeItem, getTotal, clearCart } = useCartStore()
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const total = getTotal()
  const platformFee = total * 0.2
  const creatorPayout = total * 0.8

  const handleCheckout = async () => {
    if (items.length === 0) return

    setIsProcessing(true)
    setError(null)

    try {
      // For each item, create a purchase request
      const purchasePromises = items.map(async (item) => {
        const response = await marketplaceApi.purchaseLicense({
          listing_id: item.actorId,
          license_type: item.tierName.toLowerCase(),
          usage_type: item.tierName === 'Basic' ? 'personal' : 'commercial',
          duration_days: item.tierName === 'Enterprise' ? 365 : item.tierName === 'Pro' ? 90 : 30,
        })
        return response
      })

      const results = await Promise.all(purchasePromises)

      // Get the first checkout URL (in a real app, you'd batch these)
      const checkoutUrl = results[0]?.checkout_url

      if (checkoutUrl) {
        // Clear cart and redirect to Stripe
        clearCart()
        window.location.href = checkoutUrl
      } else {
        // Demo mode - simulate success
        clearCart()
        router.push('/checkout/success')
      }
    } catch (err: unknown) {
      logger.error('Checkout error', err)
      const errorMessage = err instanceof Error ? err.message : 'Payment processing failed. Please try again.'
      setError(errorMessage)
    } finally {
      setIsProcessing(false)
    }
  }

  if (items.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
        {/* Header */}
        <header className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-xl">
          <div className="container mx-auto px-4 h-16 flex items-center justify-between">
            <Link href="/marketplace" className="flex items-center gap-2 text-slate-400 hover:text-white transition">
              <ArrowLeft className="w-5 h-5" />
              <span>Back to Marketplace</span>
            </Link>
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-white">ActorHub.ai</span>
            </Link>
            <div className="w-24" />
          </div>
        </header>

        <main className="container mx-auto px-4 py-16">
          <div className="max-w-md mx-auto text-center">
            <ShoppingCart className="w-16 h-16 text-slate-600 mx-auto mb-6" />
            <h1 className="text-2xl font-bold text-white mb-4">Your cart is empty</h1>
            <p className="text-slate-400 mb-8">
              Browse our marketplace to find actor packs to license.
            </p>
            <Button asChild className="bg-purple-600 hover:bg-purple-700">
              <Link href="/marketplace">
                Browse Marketplace
              </Link>
            </Button>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-xl">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/marketplace" className="flex items-center gap-2 text-slate-400 hover:text-white transition">
            <ArrowLeft className="w-5 h-5" />
            <span>Continue Shopping</span>
          </Link>
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-white">ActorHub.ai</span>
          </Link>
          <div className="flex items-center gap-2 text-slate-400">
            <Lock className="w-4 h-4" />
            <span className="text-sm">Secure Checkout</span>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-3xl font-bold text-white mb-8">Checkout</h1>

          <div className="grid lg:grid-cols-3 gap-8">
            {/* Order Items */}
            <div className="lg:col-span-2 space-y-4">
              <Card className="bg-slate-800/50 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <ShoppingCart className="w-5 h-5 text-purple-400" />
                    Order Items ({items.length})
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {items.map((item) => (
                    <div
                      key={item.id}
                      className="flex gap-4 p-4 bg-slate-900/50 rounded-lg border border-slate-700/50"
                    >
                      <div className="w-20 h-20 rounded-lg overflow-hidden bg-slate-700 flex-shrink-0">
                        {item.actorImage ? (
                          <img
                            src={item.actorImage}
                            alt={item.actorName}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-slate-500">
                            <Shield className="w-8 h-8" />
                          </div>
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-white">{item.actorName}</h3>
                        <p className="text-sm text-purple-400 mb-2">{item.tierName} License</p>
                        <ul className="space-y-1">
                          {item.features.slice(0, 3).map((feature, i) => (
                            <li key={i} className="flex items-center gap-1.5 text-xs text-slate-400">
                              <CheckCircle className="w-3 h-3 text-green-400" />
                              {feature}
                            </li>
                          ))}
                          {item.features.length > 3 && (
                            <li className="text-xs text-slate-500">
                              +{item.features.length - 3} more features
                            </li>
                          )}
                        </ul>
                      </div>

                      <div className="flex flex-col items-end justify-between">
                        <button
                          onClick={() => removeItem(item.id)}
                          className="text-slate-400 hover:text-red-400 transition"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                        <div className="text-right">
                          <p className="text-lg font-bold text-white">
                            {formatCurrency(item.tierPrice)}
                          </p>
                          <p className="text-xs text-slate-500">one-time</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>

              {/* Payment Security Info */}
              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <Lock className="w-5 h-5 text-green-400 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-white mb-1">Secure Payment</h4>
                      <p className="text-sm text-slate-400">
                        Your payment is processed securely through Stripe. We never store your card details.
                        All transactions are encrypted with 256-bit SSL.
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Order Summary */}
            <div className="lg:col-span-1">
              <Card className="bg-slate-800/50 border-slate-700 sticky top-24">
                <CardHeader>
                  <CardTitle className="text-white">Order Summary</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Items breakdown */}
                  <div className="space-y-2">
                    {items.map((item) => (
                      <div key={item.id} className="flex justify-between text-sm">
                        <span className="text-slate-400 truncate pr-2">
                          {item.actorName} - {item.tierName}
                        </span>
                        <span className="text-white flex-shrink-0">
                          {formatCurrency(item.tierPrice)}
                        </span>
                      </div>
                    ))}
                  </div>

                  <div className="border-t border-slate-700 pt-4 space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-400">Subtotal</span>
                      <span className="text-white">{formatCurrency(total)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-400">Platform Fee (20%)</span>
                      <span className="text-white">{formatCurrency(platformFee)}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-500">Creator Payout (80%)</span>
                      <span className="text-slate-500">{formatCurrency(creatorPayout)}</span>
                    </div>
                  </div>

                  <div className="border-t border-slate-700 pt-4">
                    <div className="flex justify-between text-lg font-bold">
                      <span className="text-white">Total</span>
                      <span className="text-white">{formatCurrency(total)}</span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      Includes all applicable fees
                    </p>
                  </div>

                  {error && (
                    <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                      <p className="text-sm text-red-400">{error}</p>
                    </div>
                  )}

                  <Button
                    onClick={handleCheckout}
                    disabled={isProcessing}
                    className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:opacity-50"
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <CreditCard className="w-4 h-4 mr-2" />
                        Pay {formatCurrency(total)}
                      </>
                    )}
                  </Button>

                  <p className="text-xs text-center text-slate-500">
                    By completing this purchase, you agree to our{' '}
                    <Link href="/terms" className="text-purple-400 hover:underline">
                      Terms of Service
                    </Link>{' '}
                    and{' '}
                    <Link href="/privacy" className="text-purple-400 hover:underline">
                      Privacy Policy
                    </Link>
                  </p>

                  {/* Payment Methods */}
                  <div className="pt-4 border-t border-slate-700">
                    <p className="text-xs text-slate-500 text-center mb-3">
                      Secure payment powered by
                    </p>
                    <div className="flex justify-center items-center gap-4">
                      <div className="flex items-center gap-1 text-slate-400">
                        <CreditCard className="w-5 h-5" />
                        <span className="text-xs">Stripe</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

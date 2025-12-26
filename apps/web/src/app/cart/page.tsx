'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { ShoppingCart, Trash2, Plus, Minus, ArrowRight, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useCartStore, CartItem } from '@/store/cart'
import { formatCurrency } from '@/lib/utils'

function CartItemRow({ item }: { item: CartItem }) {
  const { removeItem, updateQuantity } = useCartStore()

  return (
    <div className="flex gap-4 p-4 bg-slate-800/50 rounded-lg border border-slate-700/50">
      <div className="w-20 h-20 rounded-lg overflow-hidden bg-slate-700 flex-shrink-0">
        {item.actorImage ? (
          <img
            src={item.actorImage}
            alt={item.actorName}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-500">
            <ShoppingCart className="w-8 h-8" />
          </div>
        )}
      </div>

      <div className="flex-1 min-w-0">
        <h3 className="font-medium text-white text-lg">{item.actorName}</h3>
        <p className="text-purple-400">{item.tierName} Plan</p>
        <p className="text-lg font-semibold text-white mt-1">
          {formatCurrency(item.tierPrice)}
        </p>
      </div>

      <div className="flex flex-col items-end gap-3">
        <button
          onClick={() => removeItem(item.id)}
          className="text-slate-400 hover:text-red-400 transition p-1"
          aria-label={`Remove ${item.actorName} from cart`}
        >
          <Trash2 className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={() => updateQuantity(item.id, item.quantity - 1)}
            className="w-8 h-8 rounded bg-slate-700 hover:bg-slate-600 flex items-center justify-center text-slate-300 transition"
            aria-label={`Decrease quantity of ${item.actorName}`}
          >
            <Minus className="w-4 h-4" />
          </button>
          <span className="text-white w-6 text-center font-medium">{item.quantity}</span>
          <button
            onClick={() => updateQuantity(item.id, item.quantity + 1)}
            className="w-8 h-8 rounded bg-slate-700 hover:bg-slate-600 flex items-center justify-center text-slate-300 transition"
            aria-label={`Increase quantity of ${item.actorName}`}
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

export default function CartPage() {
  const { items, getTotal, getItemCount, clearCart } = useCartStore()

  // Prevent hydration issues
  const mounted = typeof window !== 'undefined'

  const itemCount = mounted ? getItemCount() : 0
  const total = mounted ? getTotal() : 0
  const displayItems = mounted ? items : []

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      <header className="border-b border-slate-800">
        <div className="container mx-auto px-4 h-16 flex items-center">
          <Link
            href="/marketplace"
            className="flex items-center gap-2 text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="w-5 h-5" />
            Continue Shopping
          </Link>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="flex items-center gap-3 mb-8">
          <ShoppingCart className="w-8 h-8 text-purple-400" />
          <h1 className="text-3xl font-bold text-white">
            Shopping Cart ({itemCount})
          </h1>
        </div>

        {displayItems.length === 0 ? (
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="p-12 text-center">
              <ShoppingCart className="w-16 h-16 text-slate-600 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-white mb-2">
                Your cart is empty
              </h2>
              <p className="text-slate-400 mb-6">
                Browse our marketplace to find actor packs
              </p>
              <Button
                className="bg-purple-600 hover:bg-purple-700"
                asChild
              >
                <Link href="/marketplace">
                  Browse Marketplace
                  <ArrowRight className="ml-2 w-4 h-4" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-4">
              {displayItems.map((item) => (
                <CartItemRow key={item.id} item={item} />
              ))}

              <div className="pt-4">
                <Button
                  variant="outline"
                  className="border-slate-700 text-slate-300"
                  onClick={clearCart}
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Clear Cart
                </Button>
              </div>
            </div>

            <div className="lg:col-span-1">
              <Card className="bg-slate-800/50 border-slate-700 sticky top-8">
                <CardHeader>
                  <CardTitle className="text-white">Order Summary</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-400">Subtotal</span>
                      <span className="text-white">{formatCurrency(total)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-400">Platform Fee (20%)</span>
                      <span className="text-white">{formatCurrency(total * 0.2)}</span>
                    </div>
                    <div className="flex justify-between font-semibold text-lg border-t border-slate-700 pt-3">
                      <span className="text-white">Total</span>
                      <span className="text-white">{formatCurrency(total)}</span>
                    </div>
                  </div>

                  <Button
                    className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700"
                    size="lg"
                    disabled={displayItems.length === 0}
                    asChild
                  >
                    <Link href="/checkout">
                      Proceed to Checkout
                      <ArrowRight className="ml-2 w-4 h-4" />
                    </Link>
                  </Button>

                  <p className="text-xs text-slate-500 text-center">
                    Secure checkout powered by Stripe
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

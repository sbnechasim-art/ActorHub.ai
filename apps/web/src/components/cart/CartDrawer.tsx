'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { X, ShoppingCart, Trash2, Plus, Minus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useCartStore, CartItem } from '@/store/cart'
import { formatCurrency, cn } from '@/lib/utils'

function CartItemCard({ item }: { item: CartItem }) {
  const { removeItem, updateQuantity } = useCartStore()

  return (
    <div className="flex gap-4 p-4 bg-slate-800/50 rounded-lg border border-slate-700/50">
      <div className="w-16 h-16 rounded-lg overflow-hidden bg-slate-700 flex-shrink-0">
        {item.actorImage ? (
          <img
            src={item.actorImage}
            alt={item.actorName}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-500">
            <ShoppingCart className="w-6 h-6" />
          </div>
        )}
      </div>

      <div className="flex-1 min-w-0">
        <h4 className="font-medium text-white truncate">{item.actorName}</h4>
        <p className="text-sm text-purple-400">{item.tierName} Plan</p>
        <p className="text-sm font-semibold text-white mt-1">
          {formatCurrency(item.tierPrice)}
        </p>
      </div>

      <div className="flex flex-col items-end gap-2">
        <button
          onClick={() => removeItem(item.id)}
          className="text-slate-400 hover:text-red-400 transition"
        >
          <Trash2 className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={() => updateQuantity(item.id, item.quantity - 1)}
            className="w-6 h-6 rounded bg-slate-700 hover:bg-slate-600 flex items-center justify-center text-slate-300 transition"
          >
            <Minus className="w-3 h-3" />
          </button>
          <span className="text-sm text-white w-4 text-center">{item.quantity}</span>
          <button
            onClick={() => updateQuantity(item.id, item.quantity + 1)}
            className="w-6 h-6 rounded bg-slate-700 hover:bg-slate-600 flex items-center justify-center text-slate-300 transition"
          >
            <Plus className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  )
}

export function CartDrawer() {
  const { items, isOpen, closeCart, getTotal, getItemCount, clearCart } = useCartStore()

  // Close on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        closeCart()
      }
    }

    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [isOpen, closeCart])

  // Prevent body scroll when drawer is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }

    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  const itemCount = getItemCount()
  const total = getTotal()

  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 bg-black/60 backdrop-blur-sm z-50 transition-opacity duration-300',
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        onClick={closeCart}
      />

      {/* Drawer */}
      <div
        className={cn(
          'fixed top-0 right-0 h-full w-full max-w-md bg-slate-900 border-l border-slate-800 z-50 transform transition-transform duration-300 ease-out flex flex-col',
          isOpen ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <ShoppingCart className="w-5 h-5 text-purple-400" />
            <h2 className="text-lg font-semibold text-white">
              Cart ({itemCount})
            </h2>
          </div>
          <button
            onClick={closeCart}
            className="text-slate-400 hover:text-white transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {items.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <ShoppingCart className="w-12 h-12 text-slate-600 mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">
                Your cart is empty
              </h3>
              <p className="text-slate-400 mb-6">
                Browse our marketplace to find actor packs
              </p>
              <Button
                onClick={closeCart}
                className="bg-purple-600 hover:bg-purple-700"
                asChild
              >
                <Link href="/marketplace">
                  Browse Marketplace
                </Link>
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {items.map((item) => (
                <CartItemCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {items.length > 0 && (
          <div className="border-t border-slate-800 p-4 space-y-4">
            {/* Summary */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Subtotal</span>
                <span className="text-white">{formatCurrency(total)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Platform Fee (20%)</span>
                <span className="text-white">{formatCurrency(total * 0.2)}</span>
              </div>
              <div className="flex justify-between font-semibold text-lg border-t border-slate-700 pt-2">
                <span className="text-white">Total</span>
                <span className="text-white">{formatCurrency(total)}</span>
              </div>
            </div>

            {/* Actions */}
            <div className="space-y-2">
              <Button
                className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700"
                asChild
              >
                <Link href="/checkout" onClick={closeCart}>
                  Proceed to Checkout
                </Link>
              </Button>
              <Button
                variant="outline"
                className="w-full border-slate-700 text-slate-300"
                onClick={clearCart}
              >
                Clear Cart
              </Button>
            </div>

            <p className="text-xs text-slate-500 text-center">
              Secure checkout powered by Stripe
            </p>
          </div>
        )}
      </div>
    </>
  )
}

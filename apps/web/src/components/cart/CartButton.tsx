'use client'

import { useEffect, useState } from 'react'
import { ShoppingCart } from 'lucide-react'
import { useCartStore } from '@/store/cart'
import { cn } from '@/lib/utils'

interface CartButtonProps {
  className?: string
}

export function CartButton({ className }: CartButtonProps) {
  const { openCart, getItemCount } = useCartStore()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Prevent hydration mismatch - show 0 until client mounts
  const itemCount = mounted ? getItemCount() : 0

  return (
    <button
      onClick={openCart}
      className={cn(
        'relative p-2 text-slate-400 hover:text-white transition rounded-lg hover:bg-slate-800/50',
        className
      )}
      aria-label={`Shopping cart with ${itemCount} items`}
    >
      <ShoppingCart className="w-5 h-5" />
      {itemCount > 0 && (
        <span className="absolute -top-1 -right-1 w-5 h-5 bg-purple-500 rounded-full text-xs font-bold text-white flex items-center justify-center">
          {itemCount > 9 ? '9+' : itemCount}
        </span>
      )}
    </button>
  )
}

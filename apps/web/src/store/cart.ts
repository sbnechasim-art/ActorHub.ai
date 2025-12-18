import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface CartItem {
  id: string
  actorId: string
  actorName: string
  actorImage: string
  tierName: string
  tierPrice: number
  features: string[]
  quantity: number
}

interface CartState {
  items: CartItem[]
  isOpen: boolean

  // Actions
  addItem: (item: Omit<CartItem, 'quantity'>) => void
  removeItem: (id: string) => void
  updateQuantity: (id: string, quantity: number) => void
  clearCart: () => void
  toggleCart: () => void
  openCart: () => void
  closeCart: () => void

  // Computed
  getTotal: () => number
  getItemCount: () => number
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],
      isOpen: false,

      addItem: (item) => {
        // Use set callback for atomic state updates
        set((state) => {
          const existingItem = state.items.find(
            (i) => i.actorId === item.actorId && i.tierName === item.tierName
          )

          if (existingItem) {
            // Item already in cart, just open cart
            return { isOpen: true }
          }

          const newItem: CartItem = {
            ...item,
            id: `${item.actorId}-${item.tierName}-${Date.now()}`,
            quantity: 1,
          }

          return { items: [...state.items, newItem], isOpen: true }
        })
      },

      removeItem: (id) => {
        // Use set callback for atomic state updates
        set((state) => ({
          items: state.items.filter((item) => item.id !== id)
        }))
      },

      updateQuantity: (id, quantity) => {
        // Use set callback for atomic state updates
        set((state) => {
          if (quantity < 1) {
            return { items: state.items.filter((item) => item.id !== id) }
          }

          return {
            items: state.items.map((item) =>
              item.id === id ? { ...item, quantity } : item
            ),
          }
        })
      },

      clearCart: () => {
        set({ items: [] })
      },

      toggleCart: () => {
        set({ isOpen: !get().isOpen })
      },

      openCart: () => {
        set({ isOpen: true })
      },

      closeCart: () => {
        set({ isOpen: false })
      },

      getTotal: () => {
        return get().items.reduce(
          (total, item) => total + item.tierPrice * item.quantity,
          0
        )
      },

      getItemCount: () => {
        return get().items.reduce((count, item) => count + item.quantity, 0)
      },
    }),
    {
      name: 'actorhub-cart',
      partialize: (state) => ({ items: state.items }),
    }
  )
)

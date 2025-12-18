import { describe, it, expect, beforeEach } from 'vitest'
import { act } from '@testing-library/react'
import { useCartStore, CartItem } from '@/store/cart'

// Helper to create cart item
const createCartItem = (overrides: Partial<Omit<CartItem, 'quantity'>> = {}): Omit<CartItem, 'quantity'> => ({
  id: `item-${Date.now()}`,
  actorId: 'actor-1',
  actorName: 'Test Actor',
  actorImage: '/test-image.jpg',
  tierName: 'Commercial',
  tierPrice: 99.00,
  features: ['Feature 1', 'Feature 2'],
  ...overrides,
})

describe('Cart Store', () => {
  beforeEach(() => {
    // Reset store before each test
    act(() => {
      useCartStore.getState().clearCart()
      useCartStore.getState().closeCart()
    })
  })

  describe('Initial State', () => {
    it('should have empty cart initially', () => {
      const { items, isOpen, getItemCount, getTotal } = useCartStore.getState()

      expect(items).toEqual([])
      expect(isOpen).toBe(false)
      expect(getItemCount()).toBe(0)
      expect(getTotal()).toBe(0)
    })
  })

  describe('Add Item', () => {
    it('should add item to cart', () => {
      const { addItem, getItemCount, getTotal } = useCartStore.getState()

      act(() => {
        addItem(createCartItem({
          actorId: 'actor-1',
          actorName: 'Test Actor',
          tierName: 'Commercial',
          tierPrice: 99.00,
        }))
      })

      const { items, isOpen } = useCartStore.getState()

      expect(items).toHaveLength(1)
      expect(items[0].actorName).toBe('Test Actor')
      expect(items[0].tierPrice).toBe(99.00)
      expect(items[0].quantity).toBe(1)
      expect(isOpen).toBe(true) // Cart opens after adding
      expect(getItemCount()).toBe(1)
      expect(getTotal()).toBe(99.00)
    })

    it('should add multiple different items', () => {
      const { addItem } = useCartStore.getState()

      act(() => {
        addItem(createCartItem({
          actorId: 'actor-1',
          actorName: 'Actor 1',
          tierName: 'Commercial',
          tierPrice: 99.00,
        }))

        addItem(createCartItem({
          actorId: 'actor-2',
          actorName: 'Actor 2',
          tierName: 'Personal',
          tierPrice: 29.00,
        }))
      })

      const { items, getItemCount, getTotal } = useCartStore.getState()

      expect(items).toHaveLength(2)
      expect(getItemCount()).toBe(2)
      expect(getTotal()).toBe(128.00)
    })

    it('should not add duplicate items (same actor and tier)', () => {
      const { addItem } = useCartStore.getState()

      act(() => {
        addItem(createCartItem({
          actorId: 'actor-1',
          tierName: 'Commercial',
          tierPrice: 99.00,
        }))

        // Try to add same actor with same tier
        addItem(createCartItem({
          actorId: 'actor-1',
          tierName: 'Commercial',
          tierPrice: 99.00,
        }))
      })

      const { items, getItemCount } = useCartStore.getState()

      expect(items).toHaveLength(1)
      expect(getItemCount()).toBe(1)
    })

    it('should allow same actor with different tier', () => {
      const { addItem } = useCartStore.getState()

      act(() => {
        addItem(createCartItem({
          actorId: 'actor-1',
          tierName: 'Personal',
          tierPrice: 29.00,
        }))

        addItem(createCartItem({
          actorId: 'actor-1',
          tierName: 'Commercial',
          tierPrice: 99.00,
        }))
      })

      const { items } = useCartStore.getState()

      expect(items).toHaveLength(2)
    })
  })

  describe('Remove Item', () => {
    it('should remove item from cart', () => {
      const { addItem } = useCartStore.getState()

      act(() => {
        addItem(createCartItem({
          actorId: 'actor-1',
          tierName: 'Commercial',
        }))
      })

      const { items: itemsAfterAdd, removeItem } = useCartStore.getState()
      expect(itemsAfterAdd).toHaveLength(1)

      const itemId = itemsAfterAdd[0].id

      act(() => {
        removeItem(itemId)
      })

      const { items, getItemCount, getTotal } = useCartStore.getState()

      expect(items).toHaveLength(0)
      expect(getItemCount()).toBe(0)
      expect(getTotal()).toBe(0)
    })

    it('should update totals after removal', () => {
      const { addItem } = useCartStore.getState()

      act(() => {
        addItem(createCartItem({
          actorId: 'actor-1',
          tierName: 'Commercial',
          tierPrice: 99.00,
        }))

        addItem(createCartItem({
          actorId: 'actor-2',
          tierName: 'Personal',
          tierPrice: 29.00,
        }))
      })

      const { items: itemsBeforeRemove, getTotal: getTotalBefore } = useCartStore.getState()
      expect(getTotalBefore()).toBe(128.00)

      const firstItemId = itemsBeforeRemove[0].id

      act(() => {
        useCartStore.getState().removeItem(firstItemId)
      })

      const { items, getItemCount, getTotal } = useCartStore.getState()

      expect(items).toHaveLength(1)
      expect(getItemCount()).toBe(1)
      expect(getTotal()).toBe(29.00)
    })
  })

  describe('Update Quantity', () => {
    it('should update item quantity', () => {
      const { addItem } = useCartStore.getState()

      act(() => {
        addItem(createCartItem({
          actorId: 'actor-1',
          tierPrice: 99.00,
        }))
      })

      const { items: itemsAfterAdd, updateQuantity } = useCartStore.getState()
      const itemId = itemsAfterAdd[0].id

      act(() => {
        updateQuantity(itemId, 3)
      })

      const { items, getItemCount, getTotal } = useCartStore.getState()

      expect(items[0].quantity).toBe(3)
      expect(getItemCount()).toBe(3)
      expect(getTotal()).toBe(297.00)
    })

    it('should remove item when quantity is set to 0', () => {
      const { addItem } = useCartStore.getState()

      act(() => {
        addItem(createCartItem({
          actorId: 'actor-1',
        }))
      })

      const { items: itemsAfterAdd, updateQuantity } = useCartStore.getState()
      const itemId = itemsAfterAdd[0].id

      act(() => {
        updateQuantity(itemId, 0)
      })

      const { items } = useCartStore.getState()

      expect(items).toHaveLength(0)
    })
  })

  describe('Clear Cart', () => {
    it('should clear all items', () => {
      const { addItem } = useCartStore.getState()

      act(() => {
        addItem(createCartItem({ actorId: 'actor-1' }))
        addItem(createCartItem({ actorId: 'actor-2' }))
      })

      expect(useCartStore.getState().items).toHaveLength(2)

      act(() => {
        useCartStore.getState().clearCart()
      })

      const { items, getItemCount, getTotal } = useCartStore.getState()

      expect(items).toHaveLength(0)
      expect(getItemCount()).toBe(0)
      expect(getTotal()).toBe(0)
    })
  })

  describe('Cart Toggle', () => {
    it('should toggle cart open/closed', () => {
      const { toggleCart } = useCartStore.getState()

      expect(useCartStore.getState().isOpen).toBe(false)

      act(() => {
        toggleCart()
      })

      expect(useCartStore.getState().isOpen).toBe(true)

      act(() => {
        toggleCart()
      })

      expect(useCartStore.getState().isOpen).toBe(false)
    })

    it('should open cart', () => {
      const { openCart } = useCartStore.getState()

      expect(useCartStore.getState().isOpen).toBe(false)

      act(() => {
        openCart()
      })

      expect(useCartStore.getState().isOpen).toBe(true)
    })

    it('should close cart', () => {
      const { openCart, closeCart } = useCartStore.getState()

      act(() => {
        openCart()
      })

      expect(useCartStore.getState().isOpen).toBe(true)

      act(() => {
        closeCart()
      })

      expect(useCartStore.getState().isOpen).toBe(false)
    })
  })

  describe('Computed Values', () => {
    it('should calculate total correctly with multiple items', () => {
      const { addItem } = useCartStore.getState()

      act(() => {
        addItem(createCartItem({
          actorId: 'actor-1',
          tierPrice: 100.00,
        }))

        addItem(createCartItem({
          actorId: 'actor-2',
          tierPrice: 50.00,
        }))

        addItem(createCartItem({
          actorId: 'actor-3',
          tierPrice: 25.50,
        }))
      })

      const { getTotal } = useCartStore.getState()

      expect(getTotal()).toBe(175.50)
    })

    it('should calculate total with quantity', () => {
      const { addItem } = useCartStore.getState()

      act(() => {
        addItem(createCartItem({
          actorId: 'actor-1',
          tierPrice: 50.00,
        }))
      })

      const { items, updateQuantity } = useCartStore.getState()

      act(() => {
        updateQuantity(items[0].id, 4)
      })

      const { getTotal } = useCartStore.getState()

      expect(getTotal()).toBe(200.00)
    })

    it('should calculate item count with quantities', () => {
      const { addItem } = useCartStore.getState()

      act(() => {
        addItem(createCartItem({ actorId: 'actor-1' }))
        addItem(createCartItem({ actorId: 'actor-2' }))
      })

      const { items, updateQuantity, getItemCount } = useCartStore.getState()

      act(() => {
        updateQuantity(items[0].id, 3)
        updateQuantity(items[1].id, 2)
      })

      expect(getItemCount()).toBe(5)
    })
  })
})

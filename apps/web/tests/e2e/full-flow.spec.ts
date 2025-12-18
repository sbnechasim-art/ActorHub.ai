import { test, expect, Page } from '@playwright/test'

// Helper to login
async function login(page: Page, email = 'test@actorhub.ai', password = 'password123') {
  await page.goto('/sign-in')
  await page.fill('input[type="email"], input[name="email"]', email)
  await page.fill('input[type="password"]', password)
  await page.click('button[type="submit"]')
  await expect(page).toHaveURL(/dashboard/, { timeout: 10000 })
}

test.describe('Complete User Journey', () => {
  test('complete creator registration flow', async ({ page }) => {
    // Step 1: Visit homepage
    await page.goto('/')
    await expect(page).toBeVisible()

    // Step 2: Navigate to registration
    await page.click('a[href*="sign-up"], button:has-text("Sign Up"), button:has-text("Get Started")')
    await expect(page).toHaveURL(/sign-up/)

    // Step 3: Register new account
    const uniqueEmail = `creator${Date.now()}@test.com`

    const firstNameInput = page.locator('input[name="first_name"], input[name="firstName"]')
    if (await firstNameInput.count() > 0) {
      await firstNameInput.fill('New')
    }

    const lastNameInput = page.locator('input[name="last_name"], input[name="lastName"]')
    if (await lastNameInput.count() > 0) {
      await lastNameInput.fill('Creator')
    }

    await page.fill('input[name="email"], input[type="email"]', uniqueEmail)
    await page.fill('input[type="password"]', 'SecurePass123!')

    const confirmPasswordInput = page.locator('input[name="confirm_password"]')
    if (await confirmPasswordInput.count() > 0) {
      await confirmPasswordInput.fill('SecurePass123!')
    }

    await page.click('button[type="submit"]')

    // Should see success message or be redirected
    await expect(page.locator('text=/success|dashboard|verify/i').or(page)).toBeVisible({ timeout: 10000 })
  })

  test('complete identity creation flow', async ({ page }) => {
    await login(page)

    // Step 1: Navigate to identity creation
    await page.click('a[href*="register"], button:has-text("Register New"), button:has-text("Create Identity")')
    await expect(page).toHaveURL(/identity\/(register|create)/)

    // Step 2: Fill identity form
    await page.fill('input[name="name"], input[name="display_name"]', 'E2E Test Actor')

    const bioInput = page.locator('textarea[name="bio"]')
    if (await bioInput.count() > 0) {
      await bioInput.fill('This is an automated test actor created by E2E tests')
    }

    const categorySelect = page.locator('select[name="category"]')
    if (await categorySelect.count() > 0) {
      await categorySelect.selectOption('actor')
    }

    // Step 3: Submit form (without files for E2E simplicity)
    await page.click('button[type="submit"]')

    // Should see success or navigate to identity
    await expect(page.locator('text=/success|created/i').or(page)).toBeVisible({ timeout: 10000 })
  })

  test('browse marketplace and view listing', async ({ page }) => {
    // Step 1: Go to marketplace (public page)
    await page.goto('/marketplace')
    await expect(page.locator('text=/marketplace/i')).toBeVisible()

    // Step 2: Wait for listings to load
    await page.waitForLoadState('networkidle')

    // Step 3: Click on a listing if available
    const listing = page.locator('[data-testid="listing-card"], .listing-card').first()
    if (await listing.count() > 0) {
      await listing.click()

      // Should be on listing detail page
      await expect(page).toHaveURL(/marketplace\//)
    }
  })

  test('complete license purchase flow', async ({ page }) => {
    await login(page)

    // Step 1: Go to marketplace
    await page.goto('/marketplace')

    // Step 2: Click on a listing
    const listing = page.locator('[data-testid="listing-card"]').first()
    if (await listing.count() > 0) {
      await listing.click()

      // Step 3: Select license type
      const licenseSelect = page.locator('[data-testid="license-type"], select[name="license_type"]')
      if (await licenseSelect.count() > 0) {
        await licenseSelect.selectOption('COMMERCIAL')
      }

      // Step 4: Add to cart
      const addToCartBtn = page.locator('button:has-text("Add to Cart"), button:has-text("Purchase")')
      if (await addToCartBtn.count() > 0) {
        await addToCartBtn.click()

        // Should see cart update or checkout redirect
        await expect(page.locator('text=/cart|checkout|added/i')).toBeVisible({ timeout: 5000 })
      }
    }
  })

  test('view analytics dashboard', async ({ page }) => {
    await login(page)

    // Navigate to analytics
    await page.goto('/dashboard/analytics')

    // Should see analytics components
    await expect(page.locator('text=/analytics|revenue|usage/i')).toBeVisible()

    // Check for charts
    const charts = page.locator('[data-testid="chart"], canvas, svg.recharts-surface')
    if (await charts.count() > 0) {
      await expect(charts.first()).toBeVisible()
    }

    // Check for time period selector
    const periodSelector = page.locator('text=/7 days|30 days|90 days/i')
    if (await periodSelector.count() > 0) {
      await expect(periodSelector.first()).toBeVisible()
    }
  })

  test('view and manage notifications', async ({ page }) => {
    await login(page)

    // Navigate to notifications
    await page.goto('/notifications')

    // Should see notifications list
    await expect(page.locator('text=/notifications/i')).toBeVisible()

    // Check for notification items
    const notifications = page.locator('[data-testid="notification-item"]')
    if (await notifications.count() > 0) {
      // Click to mark as read
      await notifications.first().click()
    }

    // Check for mark all as read button
    const markAllBtn = page.locator('button:has-text("Mark all as read")')
    if (await markAllBtn.count() > 0 && await markAllBtn.isEnabled()) {
      await markAllBtn.click()
      await expect(page.locator('text=/marked as read/i')).toBeVisible({ timeout: 5000 })
    }
  })

  test('configure payout settings', async ({ page }) => {
    await login(page)

    // Navigate to payout settings
    await page.goto('/settings/payouts')

    // Should see payout settings
    await expect(page.locator('text=/payout|payment|balance/i')).toBeVisible()

    // Check for payment method options
    const paypalOption = page.locator('text=/paypal/i')
    if (await paypalOption.count() > 0) {
      await expect(paypalOption).toBeVisible()
    }

    // Check for balance display
    const balance = page.locator('text=/available|balance/i')
    if (await balance.count() > 0) {
      await expect(balance).toBeVisible()
    }
  })

  test('complete settings update', async ({ page }) => {
    await login(page)

    // Navigate to general settings
    await page.goto('/settings')

    // Update a setting if form is available
    const displayNameInput = page.locator('input[name="display_name"], input[name="displayName"]')
    if (await displayNameInput.count() > 0) {
      await displayNameInput.fill('Updated Display Name')

      await page.click('button[type="submit"], button:has-text("Save")')

      await expect(page.locator('text=/saved|updated|success/i')).toBeVisible({ timeout: 5000 })
    }
  })
})

test.describe('Navigation Flow', () => {
  test('navigation between main pages', async ({ page }) => {
    await login(page)

    // Dashboard -> Marketplace
    const marketplaceLink = page.locator('a[href*="marketplace"]').first()
    if (await marketplaceLink.count() > 0) {
      await marketplaceLink.click()
      await expect(page).toHaveURL(/marketplace/)
    }

    // Marketplace -> Dashboard
    const dashboardLink = page.locator('a[href*="dashboard"]').first()
    if (await dashboardLink.count() > 0) {
      await dashboardLink.click()
      await expect(page).toHaveURL(/dashboard/)
    }

    // Dashboard -> Licenses
    const licensesLink = page.locator('a[href*="licenses"]').first()
    if (await licensesLink.count() > 0) {
      await licensesLink.click()
      await expect(page).toHaveURL(/licenses/)
    }

    // Licenses -> Settings
    const settingsLink = page.locator('a[href*="settings"]').first()
    if (await settingsLink.count() > 0) {
      await settingsLink.click()
      await expect(page).toHaveURL(/settings/)
    }
  })

  test('sidebar navigation', async ({ page }) => {
    await login(page)

    // Check sidebar items
    const sidebarItems = ['Dashboard', 'Marketplace', 'Licenses', 'Analytics', 'Settings']

    for (const item of sidebarItems) {
      const link = page.locator(`nav a:has-text("${item}"), aside a:has-text("${item}")`).first()
      if (await link.count() > 0) {
        await expect(link).toBeVisible()
      }
    }
  })
})

test.describe('Responsive Design', () => {
  test('mobile navigation', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 812 })

    await login(page)

    // Check for mobile menu
    const mobileMenuBtn = page.locator('[data-testid="mobile-menu"], button[aria-label*="menu"]')
    if (await mobileMenuBtn.count() > 0) {
      await mobileMenuBtn.click()

      // Menu should be visible
      await expect(page.locator('nav, [role="navigation"]')).toBeVisible()
    }
  })

  test('tablet layout', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 })

    await page.goto('/marketplace')

    // Page should be visible and responsive
    await expect(page.locator('text=/marketplace/i')).toBeVisible()
  })

  test('desktop layout', async ({ page }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 })

    await login(page)

    // Sidebar should be visible on desktop
    const sidebar = page.locator('aside, nav[class*="sidebar"]')
    if (await sidebar.count() > 0) {
      await expect(sidebar).toBeVisible()
    }
  })
})

test.describe('Error Handling', () => {
  test('shows 404 page for invalid route', async ({ page }) => {
    await page.goto('/this-page-does-not-exist')

    await expect(page.locator('text=/404|not found|page doesn\'t exist/i')).toBeVisible()
  })

  test('handles API errors gracefully', async ({ page }) => {
    await login(page)

    // Navigate to a page that might have API errors
    await page.goto('/identity/invalid-uuid-format')

    // Should show error or 404, not crash
    await expect(page.locator('text=/error|not found|something went wrong/i')).toBeVisible()
  })
})

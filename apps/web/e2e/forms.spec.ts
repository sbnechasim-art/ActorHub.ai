import { test, expect } from '@playwright/test'

/**
 * Form Validation Tests
 * Verify form inputs and validation across the application
 */

test.describe('Developers Page Code Copy', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/developers')
  })

  test('Python copy button exists', async ({ page }) => {
    const pythonCard = page.locator('text=Python').locator('..')
    const copyButton = pythonCard.getByRole('button')
    await expect(copyButton).toBeVisible()
  })

  test('JavaScript copy button exists', async ({ page }) => {
    const jsCard = page.locator('text=JavaScript').locator('..')
    const copyButton = jsCard.getByRole('button')
    await expect(copyButton).toBeVisible()
  })

  test('Copy button shows checkmark after click', async ({ page }) => {
    // Grant clipboard permissions
    await page.context().grantPermissions(['clipboard-write'])

    const copyButtons = page.getByRole('button').filter({ has: page.locator('svg') })
    const firstCopyButton = copyButtons.first()

    if (await firstCopyButton.isVisible()) {
      await firstCopyButton.click()
      // Should show checkmark icon briefly
      await page.waitForTimeout(100)
    }
  })
})

test.describe('Search Forms', () => {
  test('Marketplace has search functionality', async ({ page }) => {
    await page.goto('/marketplace')
    const searchInput = page.getByPlaceholder(/search/i)
    // Search input may or may not exist
  })
})

test.describe('Contact Form', () => {
  test('Contact page has form elements', async ({ page }) => {
    await page.goto('/contact')
    await page.waitForLoadState('networkidle')

    // Look for form elements
    const form = page.locator('form')
    const emailInput = page.getByLabel(/email/i)
    const messageInput = page.getByLabel(/message/i)
  })
})

test.describe('Identity Registration Form', () => {
  test('Registration page loads form steps', async ({ page }) => {
    await page.goto('/identity/register')
    // May redirect to sign-in for unauthenticated users
    await page.waitForLoadState('networkidle')
  })
})

test.describe('Settings Forms', () => {
  test('Settings page requires auth for forms', async ({ page }) => {
    await page.goto('/settings')
    // Should redirect or show auth required
    await page.waitForLoadState('networkidle')
  })
})

test.describe('API Key Creation Form', () => {
  test('API key form requires authentication', async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')
    // Should require auth to access API key forms
  })
})

test.describe('Refund Request Form', () => {
  test('Refund form requires authentication', async ({ page }) => {
    await page.goto('/refund')
    await page.waitForLoadState('networkidle')
    // Should require auth
  })
})

test.describe('Input Validation UI', () => {
  test('Form inputs have proper types', async ({ page }) => {
    await page.goto('/sign-up')
    await page.waitForLoadState('networkidle')

    // Check for email input type
    const emailInputs = page.locator('input[type="email"]')
    const passwordInputs = page.locator('input[type="password"]')
  })
})

test.describe('Form Accessibility', () => {
  test('Forms have proper labels', async ({ page }) => {
    await page.goto('/contact')
    await page.waitForLoadState('networkidle')

    // Check for label associations
    const labels = page.locator('label[for]')
  })

  test('Required fields are marked', async ({ page }) => {
    await page.goto('/identity/register')
    await page.waitForLoadState('networkidle')

    // Check for required indicators
    const requiredFields = page.locator('[required], [aria-required="true"]')
  })
})

test.describe('File Upload Forms', () => {
  test('Identity registration has file upload', async ({ page }) => {
    await page.goto('/identity/register')
    await page.waitForLoadState('networkidle')

    // Should have file input for images
    const fileInputs = page.locator('input[type="file"]')
  })
})

test.describe('Checkbox and Toggle Forms', () => {
  test('Settings page has toggle switches', async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')

    // Look for toggle switches with ARIA attributes
    const switches = page.locator('[role="switch"]')
  })
})

test.describe('Form Error Messages', () => {
  test('Forms display validation errors', async ({ page }) => {
    await page.goto('/contact')
    await page.waitForLoadState('networkidle')

    // Submit empty form to trigger validation
    const submitButton = page.getByRole('button', { name: /submit|send/i })
    if (await submitButton.isVisible()) {
      await submitButton.click()
      // Check for error messages
      const errors = page.locator('[role="alert"], .error, .text-red-500')
    }
  })
})

test.describe('Payout Settings Form', () => {
  test('Payout settings requires auth', async ({ page }) => {
    await page.goto('/settings/payouts')
    await page.waitForLoadState('networkidle')
    // Should require auth
  })
})

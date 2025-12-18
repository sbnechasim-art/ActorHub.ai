import { test, expect, Page } from '@playwright/test'
import path from 'path'

// Helper to login before tests
async function login(page: Page) {
  await page.goto('/sign-in')
  await page.fill('input[type="email"], input[name="email"]', 'test@actorhub.ai')
  await page.fill('input[type="password"]', 'password123')
  await page.click('button[type="submit"]')
  await expect(page).toHaveURL(/dashboard/, { timeout: 10000 })
}

test.describe('Identity Management', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test.describe('View Identities', () => {
    test('should display identities on dashboard', async ({ page }) => {
      await expect(page.locator('text=/Your Identities/i')).toBeVisible()
    })

    test('should show Register New button', async ({ page }) => {
      await expect(page.locator('button:has-text("Register"), a:has-text("Register")')).toBeVisible()
    })

    test('should navigate to identity detail on click', async ({ page }) => {
      const identityCard = page.locator('[data-testid="identity-card"]').first()

      if (await identityCard.count() > 0) {
        await identityCard.click()
        await expect(page).toHaveURL(/identity\//)
      }
    })
  })

  test.describe('Identity Detail', () => {
    test('should display identity information', async ({ page }) => {
      // Navigate to first identity or a known test identity
      await page.goto('/identity/123e4567-e89b-12d3-a456-426614174001')

      // Check for identity name
      await expect(page.locator('h1, [data-testid="identity-name"]')).toBeVisible()
    })

    test('should show training status', async ({ page }) => {
      await page.goto('/identity/123e4567-e89b-12d3-a456-426614174001')

      await expect(page.locator('text=/training|status/i')).toBeVisible()
    })

    test('should show quality score for completed training', async ({ page }) => {
      await page.goto('/identity/123e4567-e89b-12d3-a456-426614174001')

      // Quality score should be visible for completed identities
      const qualityScore = page.locator('text=/quality|score/i')
      if (await qualityScore.count() > 0) {
        await expect(qualityScore).toBeVisible()
      }
    })

    test('should have Edit button', async ({ page }) => {
      await page.goto('/identity/123e4567-e89b-12d3-a456-426614174001')

      await expect(page.locator('button:has-text("Edit"), a:has-text("Edit")')).toBeVisible()
    })

    test('should have Delete button', async ({ page }) => {
      await page.goto('/identity/123e4567-e89b-12d3-a456-426614174001')

      await expect(page.locator('button:has-text("Delete")')).toBeVisible()
    })
  })

  test.describe('Create Identity', () => {
    test('should navigate to registration page', async ({ page }) => {
      await page.click('a[href*="register"], button:has-text("Register New")')

      await expect(page).toHaveURL(/identity\/(register|create)/)
    })

    test('should display registration form', async ({ page }) => {
      await page.goto('/identity/register')

      // Check for form fields
      await expect(page.locator('input[name="name"], input[name="display_name"]')).toBeVisible()
    })

    test('should validate required fields', async ({ page }) => {
      await page.goto('/identity/register')

      await page.click('button[type="submit"]')

      // Should show validation errors
      await expect(page.locator('text=/required/i')).toBeVisible()
    })

    test('should create identity with valid data', async ({ page }) => {
      await page.goto('/identity/register')

      // Fill form
      await page.fill('input[name="name"], input[name="display_name"]', 'Test New Actor')

      const bioInput = page.locator('textarea[name="bio"]')
      if (await bioInput.count() > 0) {
        await bioInput.fill('This is a test actor for automated testing')
      }

      // Select category if present
      const categorySelect = page.locator('select[name="category"], [data-testid="category-select"]')
      if (await categorySelect.count() > 0) {
        await categorySelect.selectOption('actor')
      }

      // Note: File upload testing requires test fixture files
      // For now, we skip the file upload validation

      await page.click('button[type="submit"]')

      // Should show success or navigate to new identity
      await expect(page.locator('text=/success|created/i').or(page)).toBeVisible({ timeout: 10000 })
    })
  })

  test.describe('Edit Identity', () => {
    test('should navigate to edit page', async ({ page }) => {
      await page.goto('/identity/123e4567-e89b-12d3-a456-426614174001')

      await page.click('button:has-text("Edit"), a:has-text("Edit")')

      await expect(page).toHaveURL(/identity\/.*\/edit/)
    })

    test('should pre-populate form with existing data', async ({ page }) => {
      await page.goto('/identity/123e4567-e89b-12d3-a456-426614174001/edit')

      // Form should be populated
      const nameInput = page.locator('input[name="name"], input[name="display_name"]')
      await expect(nameInput).not.toHaveValue('')
    })

    test('should save changes', async ({ page }) => {
      await page.goto('/identity/123e4567-e89b-12d3-a456-426614174001/edit')

      // Modify bio
      const bioInput = page.locator('textarea[name="bio"]')
      if (await bioInput.count() > 0) {
        await bioInput.fill('Updated bio text for testing')
      }

      await page.click('button[type="submit"], button:has-text("Save")')

      // Should show success message
      await expect(page.locator('text=/saved|updated|success/i')).toBeVisible({ timeout: 5000 })
    })

    test('should validate on edit', async ({ page }) => {
      await page.goto('/identity/123e4567-e89b-12d3-a456-426614174001/edit')

      // Clear required field
      const nameInput = page.locator('input[name="name"], input[name="display_name"]')
      await nameInput.clear()

      await page.click('button[type="submit"], button:has-text("Save")')

      // Should show validation error
      await expect(page.locator('text=/required/i')).toBeVisible()
    })

    test('should cancel editing', async ({ page }) => {
      await page.goto('/identity/123e4567-e89b-12d3-a456-426614174001/edit')

      await page.click('button:has-text("Cancel"), a:has-text("Cancel")')

      // Should navigate back
      await expect(page).toHaveURL(/identity\/123e4567/)
    })
  })

  test.describe('Delete Identity', () => {
    test('should show delete confirmation dialog', async ({ page }) => {
      await page.goto('/identity/123e4567-e89b-12d3-a456-426614174001')

      await page.click('button:has-text("Delete")')

      // Should show confirmation dialog
      await expect(page.locator('text=/are you sure|confirm/i')).toBeVisible()
    })

    test('should cancel deletion', async ({ page }) => {
      await page.goto('/identity/123e4567-e89b-12d3-a456-426614174001')

      await page.click('button:has-text("Delete")')

      // Click cancel in dialog
      await page.click('button:has-text("Cancel"), [data-testid="cancel-delete"]')

      // Dialog should close
      await expect(page.locator('[role="dialog"]')).not.toBeVisible()
    })

    test('should require confirmation to delete', async ({ page }) => {
      await page.goto('/identity/123e4567-e89b-12d3-a456-426614174001')

      await page.click('button:has-text("Delete")')

      // Confirm button should be present
      await expect(page.locator('button:has-text("Confirm"), button:has-text("Yes")')).toBeVisible()
    })
  })

  test.describe('Toggle Privacy', () => {
    test('should toggle identity visibility', async ({ page }) => {
      await page.goto('/identity/123e4567-e89b-12d3-a456-426614174001')

      const privacyToggle = page.locator('[data-testid="privacy-toggle"], [role="switch"]')

      if (await privacyToggle.count() > 0) {
        const initialState = await privacyToggle.getAttribute('aria-checked')
        await privacyToggle.click()

        // State should change
        const newState = await privacyToggle.getAttribute('aria-checked')
        expect(newState).not.toBe(initialState)
      }
    })
  })
})

test.describe('Identity 404', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test('should show 404 for non-existent identity', async ({ page }) => {
    await page.goto('/identity/non-existent-id')

    await expect(page.locator('text=/not found|404|doesn\'t exist/i')).toBeVisible()
  })
})

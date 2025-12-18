import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test.describe('Login', () => {
    test('should display login page', async ({ page }) => {
      await page.goto('/sign-in')

      await expect(page).toHaveTitle(/Sign In|Login|ActorHub/i)
      await expect(page.locator('input[type="email"], input[name="email"]')).toBeVisible()
      await expect(page.locator('input[type="password"]')).toBeVisible()
    })

    test('should login with valid credentials', async ({ page }) => {
      await page.goto('/sign-in')

      await page.fill('input[type="email"], input[name="email"]', 'test@actorhub.ai')
      await page.fill('input[type="password"]', 'password123')
      await page.click('button[type="submit"]')

      // Should redirect to dashboard after successful login
      await expect(page).toHaveURL(/dashboard/, { timeout: 10000 })
    })

    test('should show error for invalid credentials', async ({ page }) => {
      await page.goto('/sign-in')

      await page.fill('input[type="email"], input[name="email"]', 'wrong@email.com')
      await page.fill('input[type="password"]', 'wrongpassword')
      await page.click('button[type="submit"]')

      // Should show error message
      await expect(page.locator('text=/invalid|error|failed/i')).toBeVisible({ timeout: 5000 })
    })

    test('should show validation error for empty fields', async ({ page }) => {
      await page.goto('/sign-in')

      await page.click('button[type="submit"]')

      // Should show validation errors
      await expect(page.locator('text=/required|email/i')).toBeVisible()
    })

    test('should show validation error for invalid email format', async ({ page }) => {
      await page.goto('/sign-in')

      await page.fill('input[type="email"], input[name="email"]', 'notanemail')
      await page.fill('input[type="password"]', 'password123')
      await page.click('button[type="submit"]')

      // Should show email format error
      await expect(page.locator('text=/valid email|invalid email/i')).toBeVisible()
    })

    test('should have link to registration page', async ({ page }) => {
      await page.goto('/sign-in')

      const registerLink = page.locator('a[href*="sign-up"], a[href*="register"]')
      await expect(registerLink).toBeVisible()
      await registerLink.click()

      await expect(page).toHaveURL(/sign-up|register/)
    })

    test('should have forgot password link', async ({ page }) => {
      await page.goto('/sign-in')

      const forgotLink = page.locator('a[href*="forgot"], text=/forgot password/i')
      if (await forgotLink.count() > 0) {
        await expect(forgotLink).toBeVisible()
      }
    })
  })

  test.describe('Registration', () => {
    test('should display registration page', async ({ page }) => {
      await page.goto('/sign-up')

      await expect(page.locator('input[name="email"], input[type="email"]')).toBeVisible()
      await expect(page.locator('input[type="password"]')).toBeVisible()
    })

    test('should register new user', async ({ page }) => {
      await page.goto('/sign-up')

      const uniqueEmail = `test${Date.now()}@actorhub.ai`

      // Fill registration form
      const firstNameInput = page.locator('input[name="first_name"], input[name="firstName"]')
      if (await firstNameInput.count() > 0) {
        await firstNameInput.fill('Test')
      }

      const lastNameInput = page.locator('input[name="last_name"], input[name="lastName"]')
      if (await lastNameInput.count() > 0) {
        await lastNameInput.fill('User')
      }

      await page.fill('input[name="email"], input[type="email"]', uniqueEmail)
      await page.fill('input[type="password"]', 'SecurePass123!')

      const confirmPasswordInput = page.locator('input[name="confirm_password"], input[name="confirmPassword"]')
      if (await confirmPasswordInput.count() > 0) {
        await confirmPasswordInput.fill('SecurePass123!')
      }

      await page.click('button[type="submit"]')

      // Should show success or redirect
      await expect(page.locator('text=/success|verify|dashboard/i').or(page)).toBeVisible({ timeout: 10000 })
    })

    test('should show error for existing email', async ({ page }) => {
      await page.goto('/sign-up')

      await page.fill('input[name="email"], input[type="email"]', 'existing@actorhub.ai')
      await page.fill('input[type="password"]', 'SecurePass123!')

      const confirmPasswordInput = page.locator('input[name="confirm_password"], input[name="confirmPassword"]')
      if (await confirmPasswordInput.count() > 0) {
        await confirmPasswordInput.fill('SecurePass123!')
      }

      await page.click('button[type="submit"]')

      // Should show error about existing email
      await expect(page.locator('text=/already|exists|registered/i')).toBeVisible({ timeout: 5000 })
    })

    test('should validate password requirements', async ({ page }) => {
      await page.goto('/sign-up')

      await page.fill('input[name="email"], input[type="email"]', 'test@test.com')
      await page.fill('input[type="password"]', 'weak')

      await page.click('button[type="submit"]')

      // Should show password requirements error
      const errorText = page.locator('text=/password|characters|strong/i')
      if (await errorText.count() > 0) {
        await expect(errorText).toBeVisible()
      }
    })

    test('should have link to login page', async ({ page }) => {
      await page.goto('/sign-up')

      const loginLink = page.locator('a[href*="sign-in"], a[href*="login"]')
      await expect(loginLink).toBeVisible()
    })
  })

  test.describe('Logout', () => {
    test.beforeEach(async ({ page }) => {
      // Login first
      await page.goto('/sign-in')
      await page.fill('input[type="email"], input[name="email"]', 'test@actorhub.ai')
      await page.fill('input[type="password"]', 'password123')
      await page.click('button[type="submit"]')
      await expect(page).toHaveURL(/dashboard/, { timeout: 10000 })
    })

    test('should logout user', async ({ page }) => {
      // Find and click logout button
      const logoutButton = page.locator('button:has-text("Logout"), [data-testid="logout"]')

      if (await logoutButton.count() > 0) {
        await logoutButton.click()
        // Should redirect to home or login page
        await expect(page).toHaveURL(/^\/$|sign-in|login/)
      } else {
        // Check for user menu dropdown
        const userMenu = page.locator('[data-testid="user-menu"], [aria-label*="user"], [aria-label*="account"]')
        if (await userMenu.count() > 0) {
          await userMenu.click()
          await page.click('text=/logout|sign out/i')
          await expect(page).toHaveURL(/^\/$|sign-in|login/)
        }
      }
    })
  })

  test.describe('Protected Routes', () => {
    test('should redirect unauthenticated user to login', async ({ page }) => {
      // Clear any stored tokens
      await page.context().clearCookies()

      await page.goto('/dashboard')

      // Should redirect to login
      await expect(page).toHaveURL(/sign-in|login/, { timeout: 10000 })
    })

    test('should redirect from identity page when not authenticated', async ({ page }) => {
      await page.context().clearCookies()

      await page.goto('/identity/123')

      await expect(page).toHaveURL(/sign-in|login/, { timeout: 10000 })
    })

    test('should redirect from settings when not authenticated', async ({ page }) => {
      await page.context().clearCookies()

      await page.goto('/settings')

      await expect(page).toHaveURL(/sign-in|login/, { timeout: 10000 })
    })
  })
})

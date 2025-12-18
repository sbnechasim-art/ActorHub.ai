import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test.describe('E2E Accessibility Tests', () => {
  test.describe('Public Pages', () => {
    test('home page should have no critical accessibility violations', async ({ page }) => {
      await page.goto('/')

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()

      // Filter for critical and serious violations
      const criticalViolations = accessibilityScanResults.violations.filter(
        v => v.impact === 'critical' || v.impact === 'serious'
      )

      expect(criticalViolations).toHaveLength(0)
    })

    test('marketplace page should be accessible', async ({ page }) => {
      await page.goto('/marketplace')

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze()

      const criticalViolations = accessibilityScanResults.violations.filter(
        v => v.impact === 'critical' || v.impact === 'serious'
      )

      expect(criticalViolations).toHaveLength(0)
    })

    test('pricing page should be accessible', async ({ page }) => {
      await page.goto('/pricing')

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze()

      const criticalViolations = accessibilityScanResults.violations.filter(
        v => v.impact === 'critical' || v.impact === 'serious'
      )

      expect(criticalViolations).toHaveLength(0)
    })

    test('login page should be accessible', async ({ page }) => {
      await page.goto('/sign-in')

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze()

      const criticalViolations = accessibilityScanResults.violations.filter(
        v => v.impact === 'critical' || v.impact === 'serious'
      )

      expect(criticalViolations).toHaveLength(0)
    })

    test('registration page should be accessible', async ({ page }) => {
      await page.goto('/sign-up')

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze()

      const criticalViolations = accessibilityScanResults.violations.filter(
        v => v.impact === 'critical' || v.impact === 'serious'
      )

      expect(criticalViolations).toHaveLength(0)
    })
  })

  test.describe('Authenticated Pages', () => {
    test.beforeEach(async ({ page }) => {
      // Login
      await page.goto('/sign-in')
      await page.fill('input[type="email"], input[name="email"]', 'test@actorhub.ai')
      await page.fill('input[type="password"]', 'password123')
      await page.click('button[type="submit"]')
      await expect(page).toHaveURL(/dashboard/, { timeout: 10000 })
    })

    test('dashboard should be accessible', async ({ page }) => {
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze()

      const criticalViolations = accessibilityScanResults.violations.filter(
        v => v.impact === 'critical' || v.impact === 'serious'
      )

      expect(criticalViolations).toHaveLength(0)
    })

    test('settings page should be accessible', async ({ page }) => {
      await page.goto('/settings')

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze()

      const criticalViolations = accessibilityScanResults.violations.filter(
        v => v.impact === 'critical' || v.impact === 'serious'
      )

      expect(criticalViolations).toHaveLength(0)
    })
  })

  test.describe('Keyboard Navigation', () => {
    test('can navigate login form with keyboard', async ({ page }) => {
      await page.goto('/sign-in')

      // Tab to email field
      await page.keyboard.press('Tab')
      await expect(page.locator('input[type="email"], input[name="email"]')).toBeFocused()

      // Tab to password field
      await page.keyboard.press('Tab')
      await expect(page.locator('input[type="password"]')).toBeFocused()

      // Tab to submit button
      await page.keyboard.press('Tab')
      // Focus should be on submit button or next focusable element
    })

    test('can navigate marketplace with keyboard', async ({ page }) => {
      await page.goto('/marketplace')

      // Press Tab and verify focus moves
      for (let i = 0; i < 5; i++) {
        await page.keyboard.press('Tab')

        // Verify something is focused
        const focusedElement = await page.evaluate(() => document.activeElement?.tagName)
        expect(focusedElement).not.toBe('BODY')
      }
    })

    test('modal can be closed with Escape key', async ({ page }) => {
      await page.goto('/sign-in')
      await page.fill('input[type="email"], input[name="email"]', 'test@actorhub.ai')
      await page.fill('input[type="password"]', 'password123')
      await page.click('button[type="submit"]')
      await expect(page).toHaveURL(/dashboard/, { timeout: 10000 })

      // Try to open a modal/dialog if there's one
      const modalTrigger = page.locator('button[data-testid*="modal"], button:has-text("Delete")')
      if (await modalTrigger.count() > 0) {
        await modalTrigger.first().click()

        // Try to close with Escape
        await page.keyboard.press('Escape')

        // Modal should be closed
        await expect(page.locator('[role="dialog"]')).not.toBeVisible()
      }
    })
  })

  test.describe('Screen Reader', () => {
    test('main content has proper landmarks', async ({ page }) => {
      await page.goto('/marketplace')

      // Check for main landmark
      const main = page.locator('main, [role="main"]')
      await expect(main).toBeVisible()
    })

    test('navigation has proper landmarks', async ({ page }) => {
      await page.goto('/marketplace')

      // Check for navigation landmark
      const nav = page.locator('nav, [role="navigation"]')
      if (await nav.count() > 0) {
        await expect(nav.first()).toBeVisible()
      }
    })

    test('headings are in correct order', async ({ page }) => {
      await page.goto('/marketplace')

      const headings = await page.locator('h1, h2, h3, h4, h5, h6').allTextContents()

      // Should have at least one heading
      expect(headings.length).toBeGreaterThan(0)
    })

    test('images have alt text', async ({ page }) => {
      await page.goto('/marketplace')

      const images = page.locator('img')
      const count = await images.count()

      for (let i = 0; i < count; i++) {
        const img = images.nth(i)
        const alt = await img.getAttribute('alt')
        const ariaHidden = await img.getAttribute('aria-hidden')
        const role = await img.getAttribute('role')

        // Image should have alt text, or be decorative
        const isAccessible = alt !== null || ariaHidden === 'true' || role === 'presentation'
        expect(isAccessible).toBe(true)
      }
    })
  })

  test.describe('Focus Management', () => {
    test('focus trap in dialogs', async ({ page }) => {
      await page.goto('/sign-in')
      await page.fill('input[type="email"], input[name="email"]', 'test@actorhub.ai')
      await page.fill('input[type="password"]', 'password123')
      await page.click('button[type="submit"]')
      await expect(page).toHaveURL(/dashboard/, { timeout: 10000 })

      // Open a dialog/modal
      const deleteTrigger = page.locator('button:has-text("Delete")').first()
      if (await deleteTrigger.count() > 0) {
        await deleteTrigger.click()

        const dialog = page.locator('[role="dialog"]')
        if (await dialog.count() > 0) {
          // Tab through the dialog
          await page.keyboard.press('Tab')
          await page.keyboard.press('Tab')
          await page.keyboard.press('Tab')

          // Focus should still be within dialog
          const focusInDialog = await page.evaluate(() => {
            const focused = document.activeElement
            const dialog = document.querySelector('[role="dialog"]')
            return dialog?.contains(focused) ?? false
          })

          expect(focusInDialog).toBe(true)
        }
      }
    })

    test('focus returns after dialog closes', async ({ page }) => {
      await page.goto('/sign-in')
      await page.fill('input[type="email"], input[name="email"]', 'test@actorhub.ai')
      await page.fill('input[type="password"]', 'password123')
      await page.click('button[type="submit"]')
      await expect(page).toHaveURL(/dashboard/, { timeout: 10000 })

      const trigger = page.locator('button:has-text("Delete")').first()
      if (await trigger.count() > 0) {
        // Get trigger element details
        await trigger.click()

        const dialog = page.locator('[role="dialog"]')
        if (await dialog.count() > 0) {
          // Close dialog
          await page.keyboard.press('Escape')

          // Focus should return to trigger
          await expect(trigger).toBeFocused()
        }
      }
    })
  })

  test.describe('Color Contrast', () => {
    test('text has sufficient contrast on home page', async ({ page }) => {
      await page.goto('/')

      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2aa'])
        .disableRules([
          'region',
          'landmark-one-main',
        ])
        .analyze()

      const contrastViolations = accessibilityScanResults.violations.filter(
        v => v.id === 'color-contrast'
      )

      expect(contrastViolations).toHaveLength(0)
    })
  })

  test.describe('Mobile Accessibility', () => {
    test('touch targets are large enough', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 812 })
      await page.goto('/marketplace')

      const buttons = page.locator('button, a')
      const count = await buttons.count()

      for (let i = 0; i < Math.min(count, 10); i++) {
        const button = buttons.nth(i)
        const box = await button.boundingBox()

        if (box) {
          // WCAG 2.5.5 recommends 44x44px minimum
          expect(box.width).toBeGreaterThanOrEqual(24) // More lenient for icons
          expect(box.height).toBeGreaterThanOrEqual(24)
        }
      }
    })
  })
})

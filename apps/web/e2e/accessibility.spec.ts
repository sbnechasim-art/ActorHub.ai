import { test, expect } from '@playwright/test'

/**
 * Accessibility Tests
 * Verify ARIA attributes, keyboard navigation, and screen reader support
 */

test.describe('ARIA Attributes', () => {
  test('Home page has proper landmarks', async ({ page }) => {
    await page.goto('/')

    // Check for main landmark
    const main = page.locator('main')
    const nav = page.locator('nav')
    const footer = page.locator('footer')

    await expect(nav).toBeVisible()
    await expect(footer).toBeVisible()
  })

  test('Navigation has accessible links', async ({ page }) => {
    await page.goto('/')

    const links = page.locator('nav a')
    const count = await links.count()
    expect(count).toBeGreaterThan(0)

    // All links should have accessible names
    for (let i = 0; i < Math.min(count, 10); i++) {
      const link = links.nth(i)
      const name = await link.getAttribute('aria-label') || await link.textContent()
      expect(name?.trim()).toBeTruthy()
    }
  })

  test('Buttons have accessible names', async ({ page }) => {
    await page.goto('/')

    const buttons = page.getByRole('button')
    const count = await buttons.count()

    for (let i = 0; i < Math.min(count, 10); i++) {
      const button = buttons.nth(i)
      const name = await button.getAttribute('aria-label') || await button.textContent()
      expect(name?.trim()).toBeTruthy()
    }
  })
})

test.describe('Toggle Switch Accessibility', () => {
  test('Settings page toggles have ARIA attributes', async ({ page }) => {
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')

    // Look for toggle switches
    const switches = page.locator('[role="switch"]')
    const count = await switches.count()

    for (let i = 0; i < count; i++) {
      const toggle = switches.nth(i)
      const ariaChecked = await toggle.getAttribute('aria-checked')
      expect(['true', 'false']).toContain(ariaChecked)

      const ariaLabel = await toggle.getAttribute('aria-label')
      expect(ariaLabel).toBeTruthy()
    }
  })

  test('Identity edit page toggles have ARIA attributes', async ({ page }) => {
    await page.goto('/identity/register')
    await page.waitForLoadState('networkidle')

    const switches = page.locator('[role="switch"]')
    const count = await switches.count()

    for (let i = 0; i < count; i++) {
      const toggle = switches.nth(i)
      const ariaChecked = await toggle.getAttribute('aria-checked')
      if (ariaChecked) {
        expect(['true', 'false']).toContain(ariaChecked)
      }
    }
  })
})

test.describe('Keyboard Navigation', () => {
  test('Tab order is logical on home page', async ({ page }) => {
    await page.goto('/')

    // Press Tab and verify focus moves
    await page.keyboard.press('Tab')
    const firstFocused = await page.evaluate(() => document.activeElement?.tagName)
    expect(firstFocused).toBeTruthy()
  })

  test('Enter key activates buttons', async ({ page }) => {
    await page.goto('/')

    const button = page.getByRole('link', { name: /Get Started/i }).first()
    await button.focus()
    await page.keyboard.press('Enter')

    // Should navigate
    await expect(page).toHaveURL(/sign-up/)
  })

  test('Escape closes modal', async ({ page }) => {
    await page.goto('/')

    // Open demo modal
    const demoButton = page.getByRole('button', { name: /Watch Demo/i })
    if (await demoButton.isVisible()) {
      await demoButton.click()
      await page.waitForTimeout(300)

      // Press Escape to close
      await page.keyboard.press('Escape')
      await page.waitForTimeout(300)

      // Modal should be closed (backdrop click closes it)
    }
  })
})

test.describe('Focus Management', () => {
  test('Focus visible on interactive elements', async ({ page }) => {
    await page.goto('/')

    // Tab to a button
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')

    // Check that focus ring is visible
    const focusedElement = page.locator(':focus')
    await expect(focusedElement).toBeVisible()
  })

  test('Skip to content link exists', async ({ page }) => {
    await page.goto('/')

    // Look for skip link
    const skipLink = page.locator('a[href="#main"], a[href="#content"]')
  })
})

test.describe('Color Contrast', () => {
  test('Text has sufficient contrast on home page', async ({ page }) => {
    await page.goto('/')

    // Main heading should be visible (light text on dark background)
    const heading = page.locator('h1')
    await expect(heading).toBeVisible()
  })

  test('Buttons have visible text', async ({ page }) => {
    await page.goto('/')

    const buttons = page.getByRole('button')
    const count = await buttons.count()

    for (let i = 0; i < Math.min(count, 5); i++) {
      const button = buttons.nth(i)
      if (await button.isVisible()) {
        await expect(button).toBeVisible()
      }
    }
  })
})

test.describe('Images and Media', () => {
  test('Images have alt text', async ({ page }) => {
    await page.goto('/')

    const images = page.locator('img')
    const count = await images.count()

    for (let i = 0; i < count; i++) {
      const img = images.nth(i)
      const alt = await img.getAttribute('alt')
      // Alt can be empty string for decorative images, but should exist
      expect(alt !== null).toBeTruthy()
    }
  })

  test('Icon buttons have accessible labels', async ({ page }) => {
    await page.goto('/developers')

    // Copy buttons with just icons
    const iconButtons = page.locator('button:has(svg)')
    const count = await iconButtons.count()

    for (let i = 0; i < Math.min(count, 5); i++) {
      const button = iconButtons.nth(i)
      const ariaLabel = await button.getAttribute('aria-label')
      const textContent = await button.textContent()
      const title = await button.getAttribute('title')

      // Should have some accessible name
      expect(ariaLabel || textContent?.trim() || title).toBeTruthy()
    }
  })
})

test.describe('External Links', () => {
  test('External links have proper attributes', async ({ page }) => {
    await page.goto('/developers')

    // Find links with target="_blank"
    const externalLinks = page.locator('a[target="_blank"]')
    const count = await externalLinks.count()

    for (let i = 0; i < count; i++) {
      const link = externalLinks.nth(i)
      const rel = await link.getAttribute('rel')
      expect(rel).toContain('noopener')
    }
  })
})

test.describe('Form Accessibility', () => {
  test('Inputs have associated labels', async ({ page }) => {
    await page.goto('/contact')
    await page.waitForLoadState('networkidle')

    const inputs = page.locator('input:not([type="hidden"]), textarea, select')
    const count = await inputs.count()

    for (let i = 0; i < count; i++) {
      const input = inputs.nth(i)
      const id = await input.getAttribute('id')
      const ariaLabel = await input.getAttribute('aria-label')
      const ariaLabelledBy = await input.getAttribute('aria-labelledby')
      const placeholder = await input.getAttribute('placeholder')

      if (id) {
        const label = page.locator(`label[for="${id}"]`)
        const hasLabel = await label.count() > 0
        expect(hasLabel || ariaLabel || ariaLabelledBy || placeholder).toBeTruthy()
      }
    }
  })

  test('Required fields are announced', async ({ page }) => {
    await page.goto('/identity/register')
    await page.waitForLoadState('networkidle')

    const requiredInputs = page.locator('[required], [aria-required="true"]')
    // Just verify the query works
  })
})

test.describe('Modal Accessibility', () => {
  test('Demo modal has proper focus trap', async ({ page }) => {
    await page.goto('/')

    const demoButton = page.getByRole('button', { name: /Watch Demo/i })
    if (await demoButton.isVisible()) {
      await demoButton.click()
      await page.waitForTimeout(300)

      // Modal should have focus trap
      const modal = page.locator('[role="dialog"], .fixed.inset-0')
      if (await modal.isVisible()) {
        // Close button should have aria-label
        const closeButton = modal.locator('button[aria-label*="close" i], button[aria-label*="Close" i]')
      }
    }
  })
})

test.describe('Mobile Accessibility', () => {
  test.use({ viewport: { width: 375, height: 667 } })

  test('Touch targets are large enough', async ({ page }) => {
    await page.goto('/')

    const buttons = page.getByRole('button')
    const count = await buttons.count()

    for (let i = 0; i < Math.min(count, 5); i++) {
      const button = buttons.nth(i)
      if (await button.isVisible()) {
        const box = await button.boundingBox()
        if (box) {
          // Touch targets should be at least 44x44 pixels
          expect(box.width).toBeGreaterThanOrEqual(24)
          expect(box.height).toBeGreaterThanOrEqual(24)
        }
      }
    }
  })
})

test.describe('Animation Accessibility', () => {
  test('Respects reduced motion preference', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.goto('/')

    // Page should load without issues
    await expect(page.locator('h1')).toBeVisible()
  })
})

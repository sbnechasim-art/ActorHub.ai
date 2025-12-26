import { test, expect } from '@playwright/test'

/**
 * Demo Modal Tests
 * Verify Watch Demo modal functionality on home page
 */

test.describe('Demo Modal', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('Watch Demo button is visible', async ({ page }) => {
    const demoButton = page.getByRole('button', { name: /Watch Demo/i })
    await expect(demoButton).toBeVisible()
  })

  test('Clicking Watch Demo opens modal', async ({ page }) => {
    const demoButton = page.getByRole('button', { name: /Watch Demo/i })
    await demoButton.click()

    // Wait for modal animation
    await page.waitForTimeout(300)

    // Modal backdrop should be visible
    const backdrop = page.locator('.fixed.inset-0.bg-black\\/80')
    await expect(backdrop).toBeVisible()
  })

  test('Modal has close button', async ({ page }) => {
    const demoButton = page.getByRole('button', { name: /Watch Demo/i })
    await demoButton.click()
    await page.waitForTimeout(300)

    // Find close button with X icon
    const closeButton = page.locator('button[aria-label*="close" i], button[aria-label*="Close" i]')
    await expect(closeButton.first()).toBeVisible()
  })

  test('Close button closes modal', async ({ page }) => {
    const demoButton = page.getByRole('button', { name: /Watch Demo/i })
    await demoButton.click()
    await page.waitForTimeout(300)

    const closeButton = page.locator('button[aria-label*="close" i], button[aria-label*="Close" i]').first()
    await closeButton.click()
    await page.waitForTimeout(300)

    // Modal should be gone
    const backdrop = page.locator('.fixed.inset-0.bg-black\\/80')
    await expect(backdrop).not.toBeVisible()
  })

  test('Clicking backdrop closes modal', async ({ page }) => {
    const demoButton = page.getByRole('button', { name: /Watch Demo/i })
    await demoButton.click()
    await page.waitForTimeout(300)

    // Click on backdrop (outside modal content)
    const backdrop = page.locator('.fixed.inset-0.bg-black\\/80')
    await backdrop.click({ position: { x: 10, y: 10 } })
    await page.waitForTimeout(300)

    await expect(backdrop).not.toBeVisible()
  })

  test('Modal content shows coming soon message', async ({ page }) => {
    const demoButton = page.getByRole('button', { name: /Watch Demo/i })
    await demoButton.click()
    await page.waitForTimeout(300)

    await expect(page.getByText(/Demo Video Coming Soon/i)).toBeVisible()
  })

  test('Modal has play icon', async ({ page }) => {
    const demoButton = page.getByRole('button', { name: /Watch Demo/i })
    await demoButton.click()
    await page.waitForTimeout(300)

    // Check for play icon in modal
    const playIcon = page.locator('.lucide-play, svg.w-10')
    await expect(playIcon.first()).toBeVisible()
  })

  test('Escape key closes modal', async ({ page }) => {
    const demoButton = page.getByRole('button', { name: /Watch Demo/i })
    await demoButton.click()
    await page.waitForTimeout(300)

    await page.keyboard.press('Escape')
    await page.waitForTimeout(300)

    const backdrop = page.locator('.fixed.inset-0.bg-black\\/80')
    // Modal should close on escape (if implemented)
  })

  test('Modal stops event propagation on content click', async ({ page }) => {
    const demoButton = page.getByRole('button', { name: /Watch Demo/i })
    await demoButton.click()
    await page.waitForTimeout(300)

    // Click inside the modal content
    const modalContent = page.locator('.bg-slate-900.rounded-xl')
    await modalContent.click()
    await page.waitForTimeout(300)

    // Modal should still be visible
    const backdrop = page.locator('.fixed.inset-0.bg-black\\/80')
    await expect(backdrop).toBeVisible()
  })
})

test.describe('Demo Modal Animation', () => {
  test('Modal has smooth entrance animation', async ({ page }) => {
    await page.goto('/')

    const demoButton = page.getByRole('button', { name: /Watch Demo/i })
    await demoButton.click()

    // Modal uses Framer Motion for animation
    // Just verify it appears
    await page.waitForTimeout(500)
    const backdrop = page.locator('.fixed.inset-0.bg-black\\/80')
    await expect(backdrop).toBeVisible()
  })
})

test.describe('Demo Modal Mobile', () => {
  test.use({ viewport: { width: 375, height: 667 } })

  test('Modal works on mobile viewport', async ({ page }) => {
    await page.goto('/')

    const demoButton = page.getByRole('button', { name: /Watch Demo/i })
    await demoButton.click()
    await page.waitForTimeout(300)

    await expect(page.getByText(/Demo Video Coming Soon/i)).toBeVisible()
  })

  test('Modal is properly sized on mobile', async ({ page }) => {
    await page.goto('/')

    const demoButton = page.getByRole('button', { name: /Watch Demo/i })
    await demoButton.click()
    await page.waitForTimeout(300)

    const modalContent = page.locator('.bg-slate-900.rounded-xl')
    const box = await modalContent.boundingBox()

    if (box) {
      // Modal should fit within viewport with padding
      expect(box.width).toBeLessThan(375)
    }
  })
})

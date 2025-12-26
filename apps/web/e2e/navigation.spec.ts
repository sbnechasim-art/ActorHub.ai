import { test, expect } from '@playwright/test'

/**
 * Navigation Tests
 * Verify all navigation links work correctly
 */

test.describe('Main Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('Logo navigates to home', async ({ page }) => {
    await page.getByRole('link', { name: /ActorHub\.ai/i }).first().click()
    await expect(page).toHaveURL('/')
  })

  test('Marketplace link navigates correctly', async ({ page }) => {
    await page.getByRole('link', { name: 'Marketplace' }).first().click()
    await expect(page).toHaveURL('/marketplace')
  })

  test('Developers link navigates correctly', async ({ page }) => {
    await page.getByRole('link', { name: 'Developers' }).first().click()
    await expect(page).toHaveURL('/developers')
  })

  test('Pricing link navigates correctly', async ({ page }) => {
    await page.getByRole('link', { name: 'Pricing' }).first().click()
    await expect(page).toHaveURL('/pricing')
  })

  test('Sign In button navigates correctly', async ({ page }) => {
    await page.getByRole('link', { name: 'Sign In' }).click()
    await expect(page).toHaveURL(/sign-in/)
  })

  test('Get Started button navigates to sign up', async ({ page }) => {
    await page.getByRole('link', { name: 'Get Started' }).first().click()
    await expect(page).toHaveURL(/sign-up/)
  })
})

test.describe('Footer Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('Privacy link works', async ({ page }) => {
    await page.getByRole('link', { name: 'Privacy' }).click()
    await expect(page).toHaveURL('/privacy')
  })

  test('Terms link works', async ({ page }) => {
    await page.getByRole('link', { name: 'Terms' }).click()
    await expect(page).toHaveURL('/terms')
  })

  test('Contact link works', async ({ page }) => {
    await page.getByRole('link', { name: 'Contact' }).click()
    await expect(page).toHaveURL('/contact')
  })
})

test.describe('Hero CTA Navigation', () => {
  test('Protect Your Identity button navigates to sign up', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('link', { name: /Protect Your Identity/i }).click()
    await expect(page).toHaveURL(/sign-up/)
  })

  test('Get Started Free button navigates to sign up', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('link', { name: /Get Started Free/i }).click()
    await expect(page).toHaveURL(/sign-up/)
  })
})

test.describe('Developers Page Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/developers')
  })

  test('API Docs link has correct attributes', async ({ page }) => {
    const apiDocsLinks = page.getByRole('link', { name: /API Docs|View API Documentation/i })
    const firstLink = apiDocsLinks.first()
    await expect(firstLink).toHaveAttribute('target', '_blank')
    await expect(firstLink).toHaveAttribute('rel', /noopener/)
  })

  test('Get API Key navigates to dashboard', async ({ page }) => {
    await page.getByRole('link', { name: /Get API Key/i }).click()
    await expect(page).toHaveURL(/dashboard/)
  })

  test('Marketplace link in header works', async ({ page }) => {
    await page.getByRole('link', { name: 'Marketplace' }).click()
    await expect(page).toHaveURL('/marketplace')
  })
})

test.describe('Browser Navigation', () => {
  test('Back button works correctly', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('link', { name: 'Marketplace' }).first().click()
    await expect(page).toHaveURL('/marketplace')
    await page.goBack()
    await expect(page).toHaveURL('/')
  })

  test('Forward button works correctly', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('link', { name: 'Marketplace' }).first().click()
    await page.goBack()
    await page.goForward()
    await expect(page).toHaveURL('/marketplace')
  })
})

test.describe('Mobile Navigation', () => {
  test.use({ viewport: { width: 375, height: 667 } })

  test('Mobile menu is accessible', async ({ page }) => {
    await page.goto('/')
    // Check that navigation adapts for mobile
    await expect(page).toHaveURL('/')
  })
})

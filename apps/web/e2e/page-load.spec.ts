import { test, expect } from '@playwright/test'

/**
 * Page Load Tests
 * Verify all pages load correctly with proper content
 */

test.describe('Public Pages Load', () => {
  test('Home page loads with hero section', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/ActorHub/i)
    await expect(page.locator('h1')).toContainText('Digital Identity')
    await expect(page.getByRole('link', { name: /Protect Your Identity/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /Watch Demo/i })).toBeVisible()
  })

  test('Home page stats section visible', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText(/50K\+/)).toBeVisible()
    await expect(page.getByText(/Identities Protected/i)).toBeVisible()
    await expect(page.getByText(/\$2M\+/)).toBeVisible()
    await expect(page.getByText(/99\.9%/)).toBeVisible()
  })

  test('Marketplace page loads', async ({ page }) => {
    await page.goto('/marketplace')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  })

  test('Developers page loads with API docs link', async ({ page }) => {
    await page.goto('/developers')
    await expect(page.getByText('Build with ActorHub.ai API')).toBeVisible()
    await expect(page.getByRole('link', { name: /View API Docs/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /Get API Key/i })).toBeVisible()
  })

  test('Developers page shows code examples', async ({ page }) => {
    await page.goto('/developers')
    await expect(page.getByText('Quick Start')).toBeVisible()
    await expect(page.getByText('Python')).toBeVisible()
    await expect(page.getByText('JavaScript')).toBeVisible()
  })

  test('Pricing page loads', async ({ page }) => {
    await page.goto('/pricing')
    await expect(page).toHaveURL('/pricing')
  })

  test('Sign in page loads', async ({ page }) => {
    await page.goto('/sign-in')
    await expect(page).toHaveURL(/sign-in/)
  })

  test('Sign up page loads', async ({ page }) => {
    await page.goto('/sign-up')
    await expect(page).toHaveURL(/sign-up/)
  })

  test('Privacy page loads', async ({ page }) => {
    await page.goto('/privacy')
    await expect(page).toHaveURL('/privacy')
  })

  test('Terms page loads', async ({ page }) => {
    await page.goto('/terms')
    await expect(page).toHaveURL('/terms')
  })

  test('Contact page loads', async ({ page }) => {
    await page.goto('/contact')
    await expect(page).toHaveURL('/contact')
  })
})

test.describe('Page Load Performance', () => {
  test('Home page loads within 3 seconds', async ({ page }) => {
    const startTime = Date.now()
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    const loadTime = Date.now() - startTime
    expect(loadTime).toBeLessThan(3000)
  })

  test('Marketplace page loads within 5 seconds', async ({ page }) => {
    const startTime = Date.now()
    await page.goto('/marketplace')
    await page.waitForLoadState('domcontentloaded')
    const loadTime = Date.now() - startTime
    expect(loadTime).toBeLessThan(5000)
  })
})

test.describe('Error Pages', () => {
  test('404 page for non-existent route', async ({ page }) => {
    const response = await page.goto('/non-existent-page-12345')
    expect(response?.status()).toBe(404)
  })
})

test.describe('Meta Tags', () => {
  test('Home page has proper meta description', async ({ page }) => {
    await page.goto('/')
    const description = await page.locator('meta[name="description"]').getAttribute('content')
    expect(description).toBeTruthy()
  })

  test('Home page has Open Graph tags', async ({ page }) => {
    await page.goto('/')
    const ogTitle = await page.locator('meta[property="og:title"]').getAttribute('content')
    expect(ogTitle).toBeTruthy()
  })
})

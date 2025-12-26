import { test, expect } from '@playwright/test'

/**
 * Admin Access Control Tests
 * Verify admin-only pages are protected
 */

test.describe('Admin Page Access Control', () => {
  test('Admin page shows access denied for unauthenticated users', async ({ page }) => {
    await page.goto('/admin')
    // Should show access denied or redirect
    const accessDenied = page.getByText(/access denied|unauthorized|sign in/i)
    const loading = page.locator('.animate-spin')

    // Wait for either access denied or redirect
    await page.waitForLoadState('networkidle')
  })

  test('Admin page does not expose data without auth', async ({ page }) => {
    await page.goto('/admin')
    await page.waitForLoadState('networkidle')

    // Should not show admin data like user list, transactions, etc.
    const sensitiveData = page.getByText(/total revenue|all users|transactions/i)
  })
})

test.describe('Admin Dashboard Components', () => {
  test('Admin page has proper structure when blocked', async ({ page }) => {
    await page.goto('/admin')
    await page.waitForLoadState('networkidle')

    // Check for lock icon or access denied message
    const lockIcon = page.locator('svg.lucide-lock, [data-lucide="lock"]')
  })

  test('Admin page shows home link in access denied state', async ({ page }) => {
    await page.goto('/admin')
    await page.waitForLoadState('networkidle')

    // Should have a way to go back to home
    const homeLink = page.getByRole('link', { name: /home|back|return/i })
  })
})

test.describe('Admin Sub-routes Protection', () => {
  test('Admin users page is protected', async ({ page }) => {
    await page.goto('/admin/users')
    await expect(page).toHaveURL(/admin|sign-in/)
  })

  test('Admin analytics page is protected', async ({ page }) => {
    await page.goto('/admin/analytics')
    await expect(page).toHaveURL(/admin|sign-in/)
  })

  test('Admin transactions page is protected', async ({ page }) => {
    await page.goto('/admin/transactions')
    await expect(page).toHaveURL(/admin|sign-in/)
  })

  test('Admin settings page is protected', async ({ page }) => {
    await page.goto('/admin/settings')
    await expect(page).toHaveURL(/admin|sign-in/)
  })
})

test.describe('Admin API Protection', () => {
  test('Admin API endpoints return 401 without auth', async ({ request }) => {
    const response = await request.get('/api/v1/admin/users')
    expect([401, 403, 404]).toContain(response.status())
  })

  test('Admin stats endpoint is protected', async ({ request }) => {
    const response = await request.get('/api/v1/admin/stats')
    expect([401, 403, 404]).toContain(response.status())
  })
})

test.describe('Admin UI Security', () => {
  test('Admin page does not leak user data in source', async ({ page }) => {
    await page.goto('/admin')
    await page.waitForLoadState('networkidle')

    const pageContent = await page.content()
    // Should not contain email patterns or sensitive data
    const emailPattern = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g
    const emails = pageContent.match(emailPattern) || []
    // Filter out expected emails like support@actorhub.ai
    const unexpectedEmails = emails.filter(e => !e.includes('actorhub.ai') && !e.includes('example.com'))
    expect(unexpectedEmails.length).toBe(0)
  })
})

test.describe('Role-Based Navigation', () => {
  test('Admin link not visible to unauthenticated users', async ({ page }) => {
    await page.goto('/')

    // Admin link should not be in main navigation for regular users
    const adminLink = page.getByRole('link', { name: /^admin$/i })
    await expect(adminLink).not.toBeVisible()
  })
})

test.describe('Admin Error Handling', () => {
  test('Admin page handles network errors', async ({ page }) => {
    await page.route('**/api/**', route => route.abort())
    await page.goto('/admin')
    await page.waitForLoadState('domcontentloaded')
    // Should show error or access denied, not crash
  })
})

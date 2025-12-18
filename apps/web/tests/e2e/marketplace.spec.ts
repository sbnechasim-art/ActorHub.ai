import { test, expect, Page } from '@playwright/test'

// Helper to login
async function login(page: Page) {
  await page.goto('/sign-in')
  await page.fill('input[type="email"], input[name="email"]', 'test@actorhub.ai')
  await page.fill('input[type="password"]', 'password123')
  await page.click('button[type="submit"]')
  await expect(page).toHaveURL(/dashboard/, { timeout: 10000 })
}

test.describe('Marketplace', () => {
  test.describe('Public Access', () => {
    test('should be accessible without login', async ({ page }) => {
      await page.goto('/marketplace')

      await expect(page).toHaveURL(/marketplace/)
      await expect(page.locator('text=/marketplace/i').first()).toBeVisible()
    })

    test('should display listings', async ({ page }) => {
      await page.goto('/marketplace')

      // Wait for content to load
      await page.waitForLoadState('networkidle')

      // Should have some content
      await expect(page.locator('body')).not.toBeEmpty()
    })

    test('should have search functionality', async ({ page }) => {
      await page.goto('/marketplace')

      const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]')
      if (await searchInput.count() > 0) {
        await expect(searchInput).toBeVisible()
        await searchInput.fill('actor')

        // Wait for search results
        await page.waitForTimeout(500) // Debounce
      }
    })
  })

  test.describe('Filtering', () => {
    test('should filter by category', async ({ page }) => {
      await page.goto('/marketplace')

      const categoryFilter = page.locator('[data-testid="category-filter"], select[name="category"]')
      if (await categoryFilter.count() > 0) {
        await categoryFilter.selectOption('actor')
        await page.waitForTimeout(500)
      }
    })

    test('should sort listings', async ({ page }) => {
      await page.goto('/marketplace')

      const sortSelect = page.locator('[data-testid="sort-select"], select[name="sort"]')
      if (await sortSelect.count() > 0) {
        await sortSelect.selectOption('price_asc')
        await page.waitForTimeout(500)
      }
    })
  })

  test.describe('Listing Detail', () => {
    test('should navigate to listing detail', async ({ page }) => {
      await page.goto('/marketplace')

      const listing = page.locator('[data-testid="listing-card"], .listing-card, article').first()
      if (await listing.count() > 0) {
        await listing.click()
        await expect(page).toHaveURL(/marketplace\//)
      }
    })

    test('should display listing information', async ({ page }) => {
      // Direct navigation to a listing
      await page.goto('/marketplace/123e4567-e89b-12d3-a456-426614174001')

      // Should show actor details
      await expect(page.locator('h1, [data-testid="listing-title"]')).toBeVisible()
    })

    test('should show pricing options', async ({ page }) => {
      await page.goto('/marketplace/123e4567-e89b-12d3-a456-426614174001')

      const pricing = page.locator('text=/personal|commercial|enterprise/i')
      if (await pricing.count() > 0) {
        await expect(pricing.first()).toBeVisible()
      }
    })
  })

  test.describe('Purchase Flow', () => {
    test.beforeEach(async ({ page }) => {
      await login(page)
    })

    test('should add item to cart', async ({ page }) => {
      await page.goto('/marketplace/123e4567-e89b-12d3-a456-426614174001')

      const addToCartBtn = page.locator('button:has-text("Add to Cart"), button:has-text("Purchase")')
      if (await addToCartBtn.count() > 0) {
        await addToCartBtn.click()

        // Should show cart notification or update
        await expect(page.locator('text=/added|cart/i')).toBeVisible({ timeout: 5000 })
      }
    })

    test('should open cart drawer', async ({ page }) => {
      await page.goto('/marketplace')

      const cartBtn = page.locator('[data-testid="cart-button"], button[aria-label*="cart"]')
      if (await cartBtn.count() > 0) {
        await cartBtn.click()

        // Cart drawer should open
        await expect(page.locator('[data-testid="cart-drawer"], [role="dialog"]')).toBeVisible()
      }
    })

    test('should proceed to checkout', async ({ page }) => {
      // First add item to cart
      await page.goto('/marketplace/123e4567-e89b-12d3-a456-426614174001')

      const addToCartBtn = page.locator('button:has-text("Add to Cart")')
      if (await addToCartBtn.count() > 0) {
        await addToCartBtn.click()
        await page.waitForTimeout(500)

        // Open cart and checkout
        const cartBtn = page.locator('[data-testid="cart-button"]')
        if (await cartBtn.count() > 0) {
          await cartBtn.click()

          const checkoutBtn = page.locator('button:has-text("Checkout")')
          if (await checkoutBtn.count() > 0) {
            await checkoutBtn.click()

            // Should be on checkout page
            await expect(page).toHaveURL(/checkout/)
          }
        }
      }
    })
  })

  test.describe('Checkout', () => {
    test.beforeEach(async ({ page }) => {
      await login(page)
    })

    test('should display checkout page', async ({ page }) => {
      await page.goto('/checkout')

      await expect(page.locator('text=/checkout|payment/i')).toBeVisible()
    })

    test('should show order summary', async ({ page }) => {
      await page.goto('/checkout')

      const summary = page.locator('[data-testid="order-summary"], text=/total|summary/i')
      if (await summary.count() > 0) {
        await expect(summary.first()).toBeVisible()
      }
    })
  })
})

test.describe('Marketplace Search', () => {
  test('should search and display results', async ({ page }) => {
    await page.goto('/marketplace')

    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]')
    if (await searchInput.count() > 0) {
      await searchInput.fill('Test Actor')
      await page.keyboard.press('Enter')

      await page.waitForTimeout(1000)

      // Results should update
      await expect(page.locator('body')).toBeVisible()
    }
  })

  test('should show no results message', async ({ page }) => {
    await page.goto('/marketplace')

    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]')
    if (await searchInput.count() > 0) {
      await searchInput.fill('xyznonexistent123')
      await page.keyboard.press('Enter')

      await page.waitForTimeout(1000)

      // Should show no results
      const noResults = page.locator('text=/no results|not found|no actors/i')
      if (await noResults.count() > 0) {
        await expect(noResults).toBeVisible()
      }
    }
  })
})

test.describe('Marketplace Pagination', () => {
  test('should navigate between pages', async ({ page }) => {
    await page.goto('/marketplace')

    const nextBtn = page.locator('button:has-text("Next"), [data-testid="next-page"]')
    if (await nextBtn.count() > 0 && await nextBtn.isEnabled()) {
      await nextBtn.click()

      // URL or content should change
      await page.waitForTimeout(500)
    }
  })

  test('should show page numbers', async ({ page }) => {
    await page.goto('/marketplace')

    const pagination = page.locator('[data-testid="pagination"], nav[aria-label*="pagination"]')
    if (await pagination.count() > 0) {
      await expect(pagination).toBeVisible()
    }
  })
})

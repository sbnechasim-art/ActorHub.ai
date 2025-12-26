import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  isRateLimited,
  getRemainingRequests,
  getRateLimitConfig,
  RATE_LIMITS,
  checkOnline,
} from '@/lib/api-utils'

describe('Rate Limiting', () => {
  beforeEach(() => {
    // Clear the rate limit state between tests
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('isRateLimited', () => {
    it('should not rate limit first request', () => {
      expect(isRateLimited('/test-endpoint-1', { maxRequests: 5, windowMs: 1000 })).toBe(false)
    })

    it('should rate limit after max requests exceeded', () => {
      const endpoint = '/test-endpoint-2'
      const config = { maxRequests: 3, windowMs: 1000 }

      // Make 3 requests (should not be limited)
      expect(isRateLimited(endpoint, config)).toBe(false)
      expect(isRateLimited(endpoint, config)).toBe(false)
      expect(isRateLimited(endpoint, config)).toBe(false)

      // 4th request should be limited
      expect(isRateLimited(endpoint, config)).toBe(true)
    })

    it('should reset rate limit after window expires', () => {
      const endpoint = '/test-endpoint-3'
      const config = { maxRequests: 2, windowMs: 1000 }

      // Use up the limit
      isRateLimited(endpoint, config)
      isRateLimited(endpoint, config)
      expect(isRateLimited(endpoint, config)).toBe(true)

      // Advance time past the window
      vi.advanceTimersByTime(1100)

      // Should not be limited anymore
      expect(isRateLimited(endpoint, config)).toBe(false)
    })
  })

  describe('getRemainingRequests', () => {
    it('should return max requests for new endpoint', () => {
      expect(getRemainingRequests('/new-endpoint-1', 10)).toBe(10)
    })

    it('should decrease as requests are made', () => {
      const endpoint = '/new-endpoint-2'
      const config = { maxRequests: 5, windowMs: 1000 }

      isRateLimited(endpoint, config)
      expect(getRemainingRequests(endpoint, 5)).toBe(4)

      isRateLimited(endpoint, config)
      expect(getRemainingRequests(endpoint, 5)).toBe(3)
    })
  })

  describe('getRateLimitConfig', () => {
    it('should return auth config for auth endpoints', () => {
      const config = getRateLimitConfig('/auth/login')
      expect(config.maxRequests).toBe(5)
    })

    it('should return identity config for identity endpoints', () => {
      const config = getRateLimitConfig('/identity/register')
      expect(config.maxRequests).toBe(5)
    })

    it('should return default config for unknown endpoints', () => {
      const config = getRateLimitConfig('/unknown/endpoint')
      expect(config).toEqual(RATE_LIMITS.default)
    })
  })
})

describe('Offline Detection', () => {
  describe('checkOnline', () => {
    it('should return true when online', () => {
      // In test environment, navigator.onLine defaults to true
      expect(checkOnline()).toBe(true)
    })
  })
})

describe('Rate Limit Configurations', () => {
  it('should have stricter limits for auth endpoints', () => {
    expect(RATE_LIMITS['/auth'].maxRequests).toBeLessThan(RATE_LIMITS.default.maxRequests)
  })

  it('should have stricter limits for payment endpoints', () => {
    expect(RATE_LIMITS['/marketplace/license/purchase'].maxRequests).toBeLessThan(
      RATE_LIMITS.default.maxRequests
    )
  })

  it('should have reasonable default limits', () => {
    expect(RATE_LIMITS.default.maxRequests).toBeGreaterThanOrEqual(30)
    expect(RATE_LIMITS.default.windowMs).toBe(60000) // 1 minute
  })
})

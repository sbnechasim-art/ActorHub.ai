/**
 * API Utilities
 * Rate limiting, retry logic, and request management
 */

import { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'

// =============================================================================
// Rate Limiting
// =============================================================================

interface RateLimitConfig {
  maxRequests: number  // Maximum requests allowed
  windowMs: number     // Time window in milliseconds
}

interface RequestRecord {
  count: number
  resetTime: number
}

const requestCounts = new Map<string, RequestRecord>()

/**
 * Check if a request should be rate limited
 * @param endpoint - The API endpoint being called
 * @param config - Rate limit configuration
 * @returns true if request should be blocked
 */
export function isRateLimited(
  endpoint: string,
  config: RateLimitConfig = { maxRequests: 30, windowMs: 60000 }
): boolean {
  const now = Date.now()
  const record = requestCounts.get(endpoint)

  if (!record || now > record.resetTime) {
    // Start new window
    requestCounts.set(endpoint, {
      count: 1,
      resetTime: now + config.windowMs,
    })
    return false
  }

  if (record.count >= config.maxRequests) {
    return true
  }

  record.count++
  return false
}

/**
 * Get remaining requests for an endpoint
 */
export function getRemainingRequests(
  endpoint: string,
  maxRequests: number = 30
): number {
  const record = requestCounts.get(endpoint)
  if (!record || Date.now() > record.resetTime) {
    return maxRequests
  }
  return Math.max(0, maxRequests - record.count)
}

/**
 * Rate limit configurations for different endpoint types
 */
export const RATE_LIMITS: Record<string, RateLimitConfig> = {
  // Authentication - strict limits
  '/auth': { maxRequests: 5, windowMs: 60000 },
  '/users/login': { maxRequests: 5, windowMs: 60000 },
  '/users/register': { maxRequests: 3, windowMs: 60000 },

  // Identity operations - moderate limits
  '/identity/register': { maxRequests: 5, windowMs: 300000 }, // 5 per 5 minutes
  '/identity/verify': { maxRequests: 20, windowMs: 60000 },

  // Payment operations - strict limits
  '/marketplace/license/purchase': { maxRequests: 10, windowMs: 60000 },
  '/refunds/request': { maxRequests: 3, windowMs: 300000 },

  // General API - relaxed limits
  default: { maxRequests: 60, windowMs: 60000 }, // 60 per minute
}

/**
 * Get rate limit config for an endpoint
 */
export function getRateLimitConfig(url: string): RateLimitConfig {
  for (const [pattern, config] of Object.entries(RATE_LIMITS)) {
    if (pattern !== 'default' && url.includes(pattern)) {
      return config
    }
  }
  return RATE_LIMITS.default
}

// =============================================================================
// Retry Logic
// =============================================================================

interface RetryConfig {
  maxRetries: number
  baseDelay: number      // Base delay in ms
  maxDelay: number       // Maximum delay in ms
  retryCondition: (error: AxiosError) => boolean
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
  retryCondition: (error: AxiosError) => {
    // Retry on network errors
    if (!error.response) return true

    // Retry on 5xx server errors
    const status = error.response.status
    if (status >= 500 && status < 600) return true

    // Retry on 429 Too Many Requests
    if (status === 429) return true

    // Don't retry on client errors (4xx except 429)
    return false
  },
}

/**
 * Calculate delay with exponential backoff and jitter
 */
function calculateDelay(attempt: number, config: RetryConfig): number {
  // Exponential backoff: baseDelay * 2^attempt
  const exponentialDelay = config.baseDelay * Math.pow(2, attempt)

  // Add jitter (±25%)
  const jitter = exponentialDelay * 0.25 * (Math.random() * 2 - 1)

  // Clamp to maxDelay
  return Math.min(exponentialDelay + jitter, config.maxDelay)
}

/**
 * Sleep for specified milliseconds
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Setup retry interceptor on axios instance
 */
export function setupRetryInterceptor(
  axiosInstance: AxiosInstance,
  config: Partial<RetryConfig> = {}
): void {
  const retryConfig: RetryConfig = { ...DEFAULT_RETRY_CONFIG, ...config }

  axiosInstance.interceptors.response.use(
    response => response,
    async (error: AxiosError) => {
      const originalRequest = error.config as InternalAxiosRequestConfig & { _retryCount?: number }

      if (!originalRequest) {
        return Promise.reject(error)
      }

      // Initialize retry count
      originalRequest._retryCount = originalRequest._retryCount || 0

      // Check if we should retry
      if (
        originalRequest._retryCount >= retryConfig.maxRetries ||
        !retryConfig.retryCondition(error)
      ) {
        return Promise.reject(error)
      }

      // Increment retry count
      originalRequest._retryCount++

      // Calculate delay
      const delay = calculateDelay(originalRequest._retryCount, retryConfig)

      console.log(
        `[API Retry] Attempt ${originalRequest._retryCount}/${retryConfig.maxRetries} ` +
        `for ${originalRequest.url} after ${Math.round(delay)}ms`
      )

      // Wait before retrying
      await sleep(delay)

      // Retry the request
      return axiosInstance(originalRequest)
    }
  )
}

/**
 * Setup rate limiting interceptor on axios instance
 */
export function setupRateLimitInterceptor(axiosInstance: AxiosInstance): void {
  axiosInstance.interceptors.request.use(
    (config) => {
      const url = config.url || ''
      const rateLimitConfig = getRateLimitConfig(url)

      if (isRateLimited(url, rateLimitConfig)) {
        const error = new Error(
          `Rate limit exceeded for ${url}. Please wait before making more requests.`
        )
        error.name = 'RateLimitError'
        return Promise.reject(error)
      }

      return config
    },
    (error) => Promise.reject(error)
  )
}

// =============================================================================
// Request Deduplication
// =============================================================================

const pendingRequests = new Map<string, Promise<unknown>>()

/**
 * Generate a unique key for a request
 */
function getRequestKey(config: InternalAxiosRequestConfig): string {
  return `${config.method}-${config.url}-${JSON.stringify(config.params || {})}`
}

/**
 * Setup request deduplication interceptor
 * Prevents duplicate concurrent requests
 */
export function setupDeduplicationInterceptor(axiosInstance: AxiosInstance): void {
  axiosInstance.interceptors.request.use(
    async (config) => {
      // Only deduplicate GET requests
      if (config.method?.toLowerCase() !== 'get') {
        return config
      }

      const key = getRequestKey(config)

      // Check if there's already a pending request
      if (pendingRequests.has(key)) {
        // Wait for the existing request and cancel this one
        const existingRequest = pendingRequests.get(key)
        const response = await existingRequest

        // Create a cancellation that returns the existing response
        const cancelError = new Error('Deduplicated request')
        cancelError.name = 'DeduplicatedRequest'
        ;(cancelError as any).response = response
        return Promise.reject(cancelError)
      }

      return config
    }
  )

  axiosInstance.interceptors.response.use(
    (response) => {
      const key = getRequestKey(response.config)
      pendingRequests.delete(key)
      return response
    },
    (error) => {
      if (error.config) {
        const key = getRequestKey(error.config)
        pendingRequests.delete(key)
      }

      // If this was a deduplicated request, return the cached response
      if (error.name === 'DeduplicatedRequest' && error.response) {
        return error.response
      }

      return Promise.reject(error)
    }
  )
}

// =============================================================================
// Offline Detection
// =============================================================================

let isOnline = typeof navigator !== 'undefined' ? navigator.onLine : true
const offlineCallbacks: Set<(online: boolean) => void> = new Set()

if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    isOnline = true
    offlineCallbacks.forEach(cb => cb(true))
  })

  window.addEventListener('offline', () => {
    isOnline = false
    offlineCallbacks.forEach(cb => cb(false))
  })
}

/**
 * Check if the browser is online
 */
export function checkOnline(): boolean {
  return isOnline
}

/**
 * Subscribe to online/offline changes
 */
export function onOnlineChange(callback: (online: boolean) => void): () => void {
  offlineCallbacks.add(callback)
  return () => offlineCallbacks.delete(callback)
}

/**
 * Setup offline detection interceptor
 */
export function setupOfflineInterceptor(axiosInstance: AxiosInstance): void {
  axiosInstance.interceptors.request.use(
    (config) => {
      if (!checkOnline()) {
        const error = new Error('No internet connection. Please check your network.')
        error.name = 'OfflineError'
        return Promise.reject(error)
      }
      return config
    }
  )
}

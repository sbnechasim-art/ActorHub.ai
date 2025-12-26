import { describe, it, expect } from 'vitest'
import {
  ErrorCode,
  ApiError,
  parseApiError,
  getErrorMessage,
  getUserFriendlyError,
  isOffline,
} from '@/lib/errors'

describe('ApiError', () => {
  it('should create error with correct properties', () => {
    const error = new ApiError('Test error', ErrorCode.VALIDATION_ERROR, 400)
    expect(error.message).toBe('Test error')
    expect(error.code).toBe(ErrorCode.VALIDATION_ERROR)
    expect(error.status).toBe(400)
    expect(error.name).toBe('ApiError')
  })

  it('should mark server errors as retryable', () => {
    const serverError = new ApiError('Server error', ErrorCode.SERVER_ERROR, 500)
    expect(serverError.retryable).toBe(true)
  })

  it('should mark client errors as non-retryable', () => {
    const clientError = new ApiError('Not found', ErrorCode.NOT_FOUND, 404)
    expect(clientError.retryable).toBe(false)
  })

  it('should mark rate limit errors as retryable', () => {
    const rateLimitError = new ApiError('Rate limited', ErrorCode.RATE_LIMITED, 429)
    expect(rateLimitError.retryable).toBe(true)
  })
})

describe('parseApiError', () => {
  it('should parse axios error with detail string', () => {
    const axiosError = {
      response: {
        status: 400,
        data: {
          detail: 'Face verification failed',
        },
      },
    }

    const error = parseApiError(axiosError)
    expect(error.message).toBe('Face verification failed')
    expect(error.status).toBe(400)
    expect(error.code).toBe(ErrorCode.VALIDATION_ERROR)
  })

  it('should parse axios error with detail array', () => {
    const axiosError = {
      response: {
        status: 422,
        data: {
          detail: [
            { msg: 'Field is required' },
            { msg: 'Invalid format' },
          ],
        },
      },
    }

    const error = parseApiError(axiosError)
    expect(error.message).toBe('Field is required, Invalid format')
  })

  it('should parse axios error with error object', () => {
    const axiosError = {
      response: {
        status: 401,
        data: {
          error: {
            message: 'Unauthorized access',
            code: 'UNAUTHORIZED',
          },
        },
      },
    }

    const error = parseApiError(axiosError)
    expect(error.message).toBe('Unauthorized access')
    expect(error.code).toBe(ErrorCode.UNAUTHORIZED)
  })

  it('should handle network errors', () => {
    const networkError = new Error('Network Error')

    const error = parseApiError(networkError)
    expect(error.code).toBe(ErrorCode.NETWORK_ERROR)
  })

  it('should handle timeout errors', () => {
    const timeoutError = new Error('Request timeout')

    const error = parseApiError(timeoutError)
    expect(error.code).toBe(ErrorCode.TIMEOUT)
  })

  it('should handle unknown errors', () => {
    const error = parseApiError({})
    expect(error.code).toBe(ErrorCode.UNKNOWN)
  })
})

describe('getErrorMessage', () => {
  it('should return user-friendly message for known error codes', () => {
    expect(getErrorMessage(ErrorCode.UNAUTHORIZED)).toContain('sign in')
    expect(getErrorMessage(ErrorCode.RATE_LIMITED)).toContain('requests')
    expect(getErrorMessage(ErrorCode.NOT_FOUND)).toContain('not found')
  })

  it('should return default message for unknown code', () => {
    const message = getErrorMessage('UNKNOWN_CODE' as ErrorCode)
    expect(message).toBeTruthy()
  })
})

describe('getUserFriendlyError', () => {
  it('should return Hebrew translation for face already registered', () => {
    const error = new ApiError(
      'This face is already registered',
      ErrorCode.ALREADY_EXISTS,
      409
    )

    const friendly = getUserFriendlyError(error)
    expect(friendly.title).toBe('הזהות כבר קיימת')
    expect(friendly.message).toContain('הפנים כבר רשומות')
  })

  it('should return Hebrew translation for face not detected', () => {
    const error = new ApiError(
      'Could not detect face in image',
      ErrorCode.VALIDATION_ERROR,
      400
    )

    const friendly = getUserFriendlyError(error)
    expect(friendly.title).toBe('לא זוהו פנים')
  })

  it('should return Hebrew translation for verification failed', () => {
    const error = new ApiError(
      'Face verification failed',
      ErrorCode.VALIDATION_ERROR,
      400
    )

    const friendly = getUserFriendlyError(error)
    expect(friendly.title).toBe('אימות פנים נכשל')
  })

  it('should return Hebrew translation for unauthorized', () => {
    const error = new ApiError(
      'You must be logged in',
      ErrorCode.UNAUTHORIZED,
      401
    )

    const friendly = getUserFriendlyError(error)
    expect(friendly.title).toBe('נדרשת התחברות')
  })

  it('should fallback to API message for unknown errors', () => {
    const error = new ApiError(
      'Some specific error message',
      ErrorCode.UNKNOWN,
      500
    )

    const friendly = getUserFriendlyError(error)
    expect(friendly.message).toBe('Some specific error message')
  })
})

describe('isOffline', () => {
  it('should return false when online (default in tests)', () => {
    // In test environment, navigator.onLine defaults to true
    expect(isOffline()).toBe(false)
  })
})

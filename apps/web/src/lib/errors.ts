/**
 * Error Handling Utilities
 * Provides consistent error handling across the application
 */

// API Error Types
export enum ErrorCode {
  // Authentication
  UNAUTHORIZED = 'UNAUTHORIZED',
  SESSION_EXPIRED = 'SESSION_EXPIRED',
  INVALID_CREDENTIALS = 'INVALID_CREDENTIALS',

  // Authorization
  FORBIDDEN = 'FORBIDDEN',
  INSUFFICIENT_PERMISSIONS = 'INSUFFICIENT_PERMISSIONS',

  // Resources
  NOT_FOUND = 'NOT_FOUND',
  ALREADY_EXISTS = 'ALREADY_EXISTS',

  // Validation
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  INVALID_INPUT = 'INVALID_INPUT',

  // Rate Limiting
  RATE_LIMITED = 'RATE_LIMITED',
  QUOTA_EXCEEDED = 'QUOTA_EXCEEDED',

  // Payment
  PAYMENT_REQUIRED = 'PAYMENT_REQUIRED',
  PAYMENT_FAILED = 'PAYMENT_FAILED',

  // Server
  SERVER_ERROR = 'SERVER_ERROR',
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE',
  TIMEOUT = 'TIMEOUT',

  // Network
  NETWORK_ERROR = 'NETWORK_ERROR',
  OFFLINE = 'OFFLINE',

  // Unknown
  UNKNOWN = 'UNKNOWN',
}

// Custom API Error class
export class ApiError extends Error {
  code: ErrorCode
  status: number
  details?: Record<string, unknown>
  retryable: boolean

  constructor(
    message: string,
    code: ErrorCode,
    status: number,
    details?: Record<string, unknown>
  ) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
    this.retryable = this.isRetryable()
  }

  private isRetryable(): boolean {
    return [
      ErrorCode.SERVER_ERROR,
      ErrorCode.SERVICE_UNAVAILABLE,
      ErrorCode.TIMEOUT,
      ErrorCode.NETWORK_ERROR,
      ErrorCode.RATE_LIMITED,
    ].includes(this.code)
  }
}

// User-friendly error messages
const errorMessages: Record<ErrorCode, string> = {
  [ErrorCode.UNAUTHORIZED]: 'Please sign in to continue.',
  [ErrorCode.SESSION_EXPIRED]: 'Your session has expired. Please sign in again.',
  [ErrorCode.INVALID_CREDENTIALS]: 'Invalid email or password. Please try again.',
  [ErrorCode.FORBIDDEN]: 'You do not have permission to perform this action.',
  [ErrorCode.INSUFFICIENT_PERMISSIONS]: 'You need additional permissions to access this resource.',
  [ErrorCode.NOT_FOUND]: 'The requested resource was not found.',
  [ErrorCode.ALREADY_EXISTS]: 'This resource already exists.',
  [ErrorCode.VALIDATION_ERROR]: 'Please check your input and try again.',
  [ErrorCode.INVALID_INPUT]: 'The provided input is invalid.',
  [ErrorCode.RATE_LIMITED]: 'Too many requests. Please wait a moment and try again.',
  [ErrorCode.QUOTA_EXCEEDED]: 'You have exceeded your usage quota. Please upgrade your plan.',
  [ErrorCode.PAYMENT_REQUIRED]: 'Payment is required to continue.',
  [ErrorCode.PAYMENT_FAILED]: 'Payment processing failed. Please try again.',
  [ErrorCode.SERVER_ERROR]: 'Something went wrong on our end. Please try again later.',
  [ErrorCode.SERVICE_UNAVAILABLE]: 'Service is temporarily unavailable. Please try again in a few minutes.',
  [ErrorCode.TIMEOUT]: 'The request timed out. Please try again.',
  [ErrorCode.NETWORK_ERROR]: 'Unable to connect to the server. Please check your internet connection.',
  [ErrorCode.OFFLINE]: 'You appear to be offline. Please check your internet connection.',
  [ErrorCode.UNKNOWN]: 'An unexpected error occurred. Please try again.',
}

// Get user-friendly message for error code
export function getErrorMessage(code: ErrorCode): string {
  return errorMessages[code] || errorMessages[ErrorCode.UNKNOWN]
}

// Parse API error response
export function parseApiError(error: unknown): ApiError {
  // Handle axios errors
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const axiosError = error as {
      response?: {
        status: number
        data?: {
          error?: { message?: string; code?: string }
          detail?: string | Array<{ msg: string }>
          message?: string
        }
      }
      code?: string
      message?: string
    }

    const status = axiosError.response?.status || 0
    const data = axiosError.response?.data

    // Extract error message from response
    let message = 'An error occurred'
    if (data?.error?.message) {
      message = data.error.message
    } else if (data?.detail) {
      if (typeof data.detail === 'string') {
        message = data.detail
      } else if (Array.isArray(data.detail)) {
        message = data.detail.map(d => d.msg).join(', ')
      }
    } else if (data?.message) {
      message = data.message
    }

    // Map HTTP status to error code
    const code = mapStatusToErrorCode(status, axiosError.code)

    return new ApiError(message, code, status, data as Record<string, unknown>)
  }

  // Handle network errors
  if (error instanceof Error) {
    if (error.message.includes('Network Error') || error.message.includes('fetch')) {
      return new ApiError(
        'Unable to connect to the server',
        ErrorCode.NETWORK_ERROR,
        0
      )
    }
    if (error.message.includes('timeout')) {
      return new ApiError(
        'The request timed out',
        ErrorCode.TIMEOUT,
        0
      )
    }
    return new ApiError(error.message, ErrorCode.UNKNOWN, 0)
  }

  return new ApiError('An unexpected error occurred', ErrorCode.UNKNOWN, 0)
}

// Map HTTP status code to error code
function mapStatusToErrorCode(status: number, axiosCode?: string): ErrorCode {
  // Handle network-level errors
  if (axiosCode === 'ECONNABORTED') return ErrorCode.TIMEOUT
  if (axiosCode === 'ERR_NETWORK') return ErrorCode.NETWORK_ERROR

  // Map HTTP status codes
  switch (status) {
    case 400:
      return ErrorCode.VALIDATION_ERROR
    case 401:
      return ErrorCode.UNAUTHORIZED
    case 402:
      return ErrorCode.PAYMENT_REQUIRED
    case 403:
      return ErrorCode.FORBIDDEN
    case 404:
      return ErrorCode.NOT_FOUND
    case 409:
      return ErrorCode.ALREADY_EXISTS
    case 422:
      return ErrorCode.INVALID_INPUT
    case 429:
      return ErrorCode.RATE_LIMITED
    case 500:
      return ErrorCode.SERVER_ERROR
    case 502:
    case 503:
      return ErrorCode.SERVICE_UNAVAILABLE
    case 504:
      return ErrorCode.TIMEOUT
    default:
      if (status >= 500) return ErrorCode.SERVER_ERROR
      if (status >= 400) return ErrorCode.UNKNOWN
      return ErrorCode.UNKNOWN
  }
}

// Check if user is offline
export function isOffline(): boolean {
  return typeof navigator !== 'undefined' && !navigator.onLine
}

// Common API error patterns with user-friendly translations
const errorPatterns: Array<{ pattern: RegExp; title: string; message: string }> = [
  // Identity registration errors
  {
    pattern: /face.*already registered/i,
    title: 'הזהות כבר קיימת',
    message: 'הפנים כבר רשומות במערכת. אם זה הפנים שלך, צור קשר עם התמיכה.'
  },
  {
    pattern: /could not detect face/i,
    title: 'לא זוהו פנים',
    message: 'לא הצלחנו לזהות פנים בתמונה. נסה תמונה ברורה יותר עם תאורה טובה.'
  },
  {
    pattern: /face verification failed/i,
    title: 'אימות פנים נכשל',
    message: 'הפנים בתמונה לא תואמות לסלפי. וודא ששתי התמונות מציגות את אותו אדם.'
  },
  {
    pattern: /liveness check failed/i,
    title: 'בדיקת חיות נכשלה',
    message: 'לא הצלחנו לאמת שזו תמונה חיה. צלם סלפי חדש עם תאורה טובה.'
  },
  {
    pattern: /selfie.*expired|capture.*expired/i,
    title: 'הסלפי פג תוקף',
    message: 'הסלפי ישן מדי. צלם סלפי חדש ונסה שוב.'
  },
  {
    pattern: /image too large/i,
    title: 'קובץ גדול מדי',
    message: 'הקובץ גדול מדי (מקסימום 10MB). נסה תמונה קטנה יותר.'
  },
  {
    pattern: /invalid.*image format/i,
    title: 'פורמט לא נתמך',
    message: 'פורמט התמונה לא נתמך. השתמש ב-JPEG, PNG או WebP.'
  },
  // Authentication errors
  {
    pattern: /must be logged in|unauthorized/i,
    title: 'נדרשת התחברות',
    message: 'יש להתחבר לחשבון כדי לבצע פעולה זו.'
  },
  {
    pattern: /access denied|forbidden/i,
    title: 'אין הרשאה',
    message: 'אין לך הרשאה לבצע פעולה זו.'
  },
  // Training errors
  {
    pattern: /training.*cancelled/i,
    title: 'האימון בוטל',
    message: 'האימון בוטל בהצלחה.'
  },
  {
    pattern: /no.*in.*progress/i,
    title: 'אין אימון פעיל',
    message: 'אין אימון פעיל שניתן לבטל.'
  },
  // License errors
  {
    pattern: /license.*not found/i,
    title: 'רישיון לא נמצא',
    message: 'הרישיון המבוקש לא נמצא במערכת.'
  },
  {
    pattern: /already refunded/i,
    title: 'הוחזר כבר',
    message: 'הרישיון הזה כבר הוחזר.'
  },
  {
    pattern: /refund window expired/i,
    title: 'חלון ההחזר פג',
    message: 'עברו יותר מ-14 ימים מהרכישה. לא ניתן לבקש החזר.'
  },
  // Payment errors
  {
    pattern: /payment.*failed|stripe.*error/i,
    title: 'התשלום נכשל',
    message: 'לא הצלחנו לעבד את התשלום. נסה שוב או השתמש באמצעי תשלום אחר.'
  },
  // General errors
  {
    pattern: /rate limit|too many requests/i,
    title: 'יותר מדי בקשות',
    message: 'שלחת יותר מדי בקשות. המתן מעט ונסה שוב.'
  },
  {
    pattern: /network error|connection/i,
    title: 'בעיית חיבור',
    message: 'לא הצלחנו להתחבר לשרת. בדוק את החיבור לאינטרנט.'
  },
  {
    pattern: /no internet|offline/i,
    title: 'אין חיבור לאינטרנט',
    message: 'אין חיבור לאינטרנט. בדוק את החיבור ונסה שוב.'
  },
  {
    pattern: /timeout|timed out/i,
    title: 'הבקשה נכשלה',
    message: 'הבקשה לקחה יותר מדי זמן. נסה שוב.'
  },
  {
    pattern: /server error|internal error|500/i,
    title: 'שגיאת שרת',
    message: 'אירעה שגיאה בשרת. נסה שוב בעוד כמה דקות.'
  },
]

/**
 * Get user-friendly error from API error
 * Returns both Hebrew title and message for toast display
 */
export function getUserFriendlyError(error: unknown): { title: string; message: string } {
  const apiError = error instanceof ApiError ? error : parseApiError(error)
  const errorMessage = apiError.message.toLowerCase()

  // Check against known patterns
  for (const { pattern, title, message } of errorPatterns) {
    if (pattern.test(errorMessage)) {
      return { title, message }
    }
  }

  // Fallback: use the API error message directly if no pattern matches
  // This ensures specific errors from API are still shown to users
  if (apiError.message && apiError.message !== 'An error occurred') {
    return {
      title: 'שגיאה',
      message: apiError.message
    }
  }

  // Final fallback
  return {
    title: 'שגיאה',
    message: 'אירעה שגיאה לא צפויה. נסה שוב מאוחר יותר.'
  }
}

/**
 * Show error toast with user-friendly message
 * Import: import { showErrorToast } from '@/lib/errors'
 * Usage: showErrorToast(error)
 */
export function showErrorToast(error: unknown): void {
  // Dynamic import to avoid circular dependencies
  import('@/hooks/useToast').then(({ toast }) => {
    const { title, message } = getUserFriendlyError(error)
    toast.error(title, message)
  })
}

// Error display helper for toast/alert
export interface DisplayableError {
  title: string
  message: string
  action?: {
    label: string
    onClick: () => void
  }
}

export function getDisplayableError(error: unknown): DisplayableError {
  const apiError = error instanceof ApiError ? error : parseApiError(error)

  // Check if offline first
  if (isOffline()) {
    return {
      title: 'You are offline',
      message: 'Please check your internet connection and try again.',
      action: {
        label: 'Retry',
        onClick: () => window.location.reload(),
      },
    }
  }

  // Get appropriate title and message based on error code
  const titles: Partial<Record<ErrorCode, string>> = {
    [ErrorCode.UNAUTHORIZED]: 'Authentication Required',
    [ErrorCode.FORBIDDEN]: 'Access Denied',
    [ErrorCode.NOT_FOUND]: 'Not Found',
    [ErrorCode.RATE_LIMITED]: 'Slow Down',
    [ErrorCode.PAYMENT_REQUIRED]: 'Payment Required',
    [ErrorCode.SERVER_ERROR]: 'Server Error',
    [ErrorCode.NETWORK_ERROR]: 'Connection Error',
  }

  const result: DisplayableError = {
    title: titles[apiError.code] || 'Error',
    message: apiError.message || getErrorMessage(apiError.code),
  }

  // Add retry action for retryable errors
  if (apiError.retryable) {
    result.action = {
      label: 'Try Again',
      onClick: () => window.location.reload(),
    }
  }

  // Add sign in action for auth errors
  if (apiError.code === ErrorCode.UNAUTHORIZED || apiError.code === ErrorCode.SESSION_EXPIRED) {
    result.action = {
      label: 'Sign In',
      onClick: () => {
        window.location.href = '/sign-in'
      },
    }
  }

  return result
}

// Check if error is due to browser extension interference
export function isBrowserExtensionError(error: Error): boolean {
  const extensionPatterns = [
    'insertBefore',
    'removeChild',
    'appendChild',
    'chrome-extension',
    'moz-extension',
    'Extension context',
    'translation',
  ]

  return extensionPatterns.some(pattern =>
    error.message?.toLowerCase().includes(pattern.toLowerCase()) ||
    error.stack?.toLowerCase().includes(pattern.toLowerCase())
  )
}

// Get helpful message for browser extension errors
export function getBrowserExtensionErrorMessage(): string {
  return 'A browser extension may be interfering with this page. Try disabling extensions or using Incognito/Private mode.'
}

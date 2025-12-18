/**
 * Logger utility for consistent logging across the application
 * In production, this can be extended to send logs to external services (e.g., Sentry, LogRocket)
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogContext {
  [key: string]: unknown
}

const isDevelopment = process.env.NODE_ENV === 'development'

function formatMessage(level: LogLevel, message: string, context?: LogContext): string {
  const timestamp = new Date().toISOString()
  const contextStr = context ? ` ${JSON.stringify(context)}` : ''
  return `[${timestamp}] [${level.toUpperCase()}] ${message}${contextStr}`
}

export const logger = {
  debug: (message: string, context?: LogContext) => {
    if (isDevelopment) {
      console.debug(formatMessage('debug', message, context))
    }
  },

  info: (message: string, context?: LogContext) => {
    if (isDevelopment) {
      console.info(formatMessage('info', message, context))
    }
  },

  warn: (message: string, context?: LogContext) => {
    console.warn(formatMessage('warn', message, context))
  },

  error: (message: string, error?: Error | unknown, context?: LogContext) => {
    const errorContext = {
      ...context,
      ...(error instanceof Error
        ? { errorMessage: error.message, stack: error.stack }
        : { error: String(error) }),
    }
    console.error(formatMessage('error', message, errorContext))

    // In production, send to error tracking service
    // Example: Sentry.captureException(error, { extra: context })
  },
}

export default logger

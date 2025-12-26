'use client'

/**
 * Global Error Boundary
 * Catches errors that occur in the root layout or during initial render.
 * This is the last line of defense for errors.
 */

import { useEffect } from 'react'
import { logger } from '@/lib/logger'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log to error reporting service (e.g., Sentry)
    logger.error('Global error', error, { digest: error.digest })

    // Report to analytics
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', 'exception', {
        description: error.message,
        fatal: true,
      })
    }
  }, [error])

  return (
    <html>
      <body>
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#0f172a',
            color: '#f1f5f9',
            fontFamily: 'system-ui, sans-serif',
            padding: '2rem',
          }}
        >
          <div style={{ textAlign: 'center', maxWidth: '500px' }}>
            {/* Error Icon */}
            <div
              style={{
                width: '80px',
                height: '80px',
                borderRadius: '50%',
                backgroundColor: 'rgba(239, 68, 68, 0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 2rem',
              }}
            >
              <svg
                width="40"
                height="40"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#f87171"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>

            <h1
              style={{
                fontSize: '1.875rem',
                fontWeight: 'bold',
                marginBottom: '1rem',
              }}
            >
              Something went wrong
            </h1>

            <p
              style={{
                color: '#94a3b8',
                marginBottom: '2rem',
                lineHeight: '1.6',
              }}
            >
              We're sorry, but a critical error occurred. Please try refreshing
              the page or return to the home page.
            </p>

            {/* Error ID for support */}
            {error.digest && (
              <p
                style={{
                  color: '#64748b',
                  fontSize: '0.75rem',
                  marginBottom: '1.5rem',
                  fontFamily: 'monospace',
                }}
              >
                Error ID: {error.digest}
              </p>
            )}

            <div
              style={{
                display: 'flex',
                gap: '1rem',
                justifyContent: 'center',
                flexWrap: 'wrap',
              }}
            >
              <button
                onClick={() => reset()}
                style={{
                  backgroundColor: '#7c3aed',
                  color: 'white',
                  padding: '0.75rem 1.5rem',
                  borderRadius: '0.5rem',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '1rem',
                  fontWeight: '500',
                }}
              >
                Try Again
              </button>

              <button
                onClick={() => (window.location.href = '/')}
                style={{
                  backgroundColor: 'transparent',
                  color: '#e2e8f0',
                  padding: '0.75rem 1.5rem',
                  borderRadius: '0.5rem',
                  border: '1px solid #334155',
                  cursor: 'pointer',
                  fontSize: '1rem',
                  fontWeight: '500',
                }}
              >
                Go to Home
              </button>
            </div>

            <p
              style={{
                color: '#64748b',
                fontSize: '0.875rem',
                marginTop: '2rem',
              }}
            >
              If this problem persists, please contact{' '}
              <a
                href="mailto:support@actorhub.ai"
                style={{ color: '#a78bfa', textDecoration: 'underline' }}
              >
                support@actorhub.ai
              </a>
            </p>
          </div>
        </div>
      </body>
    </html>
  )
}

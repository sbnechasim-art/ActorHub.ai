'use client'

/**
 * Dashboard Error Boundary
 * Catches errors specific to the dashboard section.
 */

import { useEffect } from 'react'
import { AlertTriangle, RefreshCw, Home, ArrowLeft, HelpCircle } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { logger } from '@/lib/logger'

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log the error
    logger.error('Dashboard error', error, {
      digest: error.digest,
      section: 'dashboard',
    })
  }, [error])

  // Determine error type for helpful messaging
  const isNetworkError =
    error.message.includes('fetch') ||
    error.message.includes('network') ||
    error.message.includes('Failed to load')
  const isAuthError =
    error.message.includes('401') ||
    error.message.includes('unauthorized') ||
    error.message.includes('authentication')

  return (
    <div className="min-h-[60vh] flex items-center justify-center p-8">
      <div className="max-w-md w-full text-center">
        {/* Error Icon */}
        <div className="w-20 h-20 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-6">
          <AlertTriangle className="w-10 h-10 text-red-400" />
        </div>

        {/* Error Title */}
        <h2 className="text-2xl font-bold text-white mb-3">
          {isAuthError
            ? 'Session Expired'
            : isNetworkError
            ? 'Connection Error'
            : 'Dashboard Error'}
        </h2>

        {/* Error Message */}
        <p className="text-slate-400 mb-6">
          {isAuthError
            ? 'Your session has expired. Please sign in again to continue.'
            : isNetworkError
            ? 'Unable to connect to the server. Please check your connection.'
            : 'Something went wrong while loading the dashboard. Please try again.'}
        </p>

        {/* Development Error Details */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mb-6 p-3 bg-slate-800/50 rounded-lg text-left border border-slate-700">
            <p className="text-red-400 font-mono text-xs break-all">
              {error.message}
            </p>
            {error.digest && (
              <p className="text-slate-500 font-mono text-xs mt-2">
                ID: {error.digest}
              </p>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center mb-6">
          {isAuthError ? (
            <Button asChild className="bg-purple-600 hover:bg-purple-700">
              <Link href="/sign-in">Sign In</Link>
            </Button>
          ) : (
            <Button
              onClick={() => reset()}
              className="bg-purple-600 hover:bg-purple-700"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Retry
            </Button>
          )}

          <Button
            onClick={() => window.history.back()}
            variant="outline"
            className="border-slate-700 text-slate-300 hover:bg-slate-800"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Go Back
          </Button>

          <Button
            asChild
            variant="outline"
            className="border-slate-700 text-slate-300 hover:bg-slate-800"
          >
            <Link href="/">
              <Home className="w-4 h-4 mr-2" />
              Home
            </Link>
          </Button>
        </div>

        {/* Help Link */}
        <Link
          href="/help"
          className="inline-flex items-center text-sm text-slate-500 hover:text-slate-400"
        >
          <HelpCircle className="w-4 h-4 mr-1" />
          Need help?
        </Link>
      </div>
    </div>
  )
}

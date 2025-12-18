'use client'

/**
 * Admin Error Boundary
 * Catches errors specific to the admin section.
 */

import { useEffect } from 'react'
import { ShieldAlert, RefreshCw, Home, ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { logger } from '@/lib/logger'

export default function AdminError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log admin errors with extra context
    logger.error('Admin panel error', error, {
      digest: error.digest,
      section: 'admin',
      severity: 'high',
    })
  }, [error])

  const isPermissionError =
    error.message.includes('403') ||
    error.message.includes('forbidden') ||
    error.message.includes('permission')

  return (
    <div className="min-h-[60vh] flex items-center justify-center p-8">
      <div className="max-w-md w-full text-center">
        {/* Error Icon */}
        <div className="w-20 h-20 rounded-full bg-orange-500/20 flex items-center justify-center mx-auto mb-6">
          <ShieldAlert className="w-10 h-10 text-orange-400" />
        </div>

        {/* Error Title */}
        <h2 className="text-2xl font-bold text-white mb-3">
          {isPermissionError ? 'Access Denied' : 'Admin Panel Error'}
        </h2>

        {/* Error Message */}
        <p className="text-slate-400 mb-6">
          {isPermissionError
            ? 'You do not have permission to access this page. Please contact your administrator.'
            : 'An error occurred in the admin panel. This has been logged for review.'}
        </p>

        {/* Development Error Details */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mb-6 p-3 bg-slate-800/50 rounded-lg text-left border border-orange-700/50">
            <p className="text-orange-400 font-mono text-xs break-all">
              {error.message}
            </p>
            {error.digest && (
              <p className="text-slate-500 font-mono text-xs mt-2">
                Error ID: {error.digest}
              </p>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          {!isPermissionError && (
            <Button
              onClick={() => reset()}
              className="bg-orange-600 hover:bg-orange-700"
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
            <Link href="/dashboard">
              <Home className="w-4 h-4 mr-2" />
              Dashboard
            </Link>
          </Button>
        </div>

        {/* Admin Support */}
        <p className="mt-6 text-slate-500 text-sm">
          Admin support:{' '}
          <a
            href="mailto:admin@actorhub.ai"
            className="text-orange-400 hover:text-orange-300"
          >
            admin@actorhub.ai
          </a>
        </p>
      </div>
    </div>
  )
}

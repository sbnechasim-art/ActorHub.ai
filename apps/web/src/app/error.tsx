'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, RefreshCw, Home, ArrowLeft, Shield, Chrome } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { logger } from '@/lib/logger'
import { isBrowserExtensionError, getBrowserExtensionErrorMessage } from '@/lib/errors'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  const [isExtensionError, setIsExtensionError] = useState(false)

  useEffect(() => {
    // Check if this is a browser extension error
    const extensionError = isBrowserExtensionError(error)
    setIsExtensionError(extensionError)

    // Log the error to an error reporting service
    logger.error('Application error', error, {
      digest: error.digest,
      isExtensionError: extensionError,
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
    })
  }, [error])

  // Handle browser extension errors specifically
  if (isExtensionError) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-4">
        <div className="max-w-lg w-full text-center">
          {/* Extension Icon */}
          <div className="w-24 h-24 rounded-full bg-amber-500/20 flex items-center justify-center mx-auto mb-8">
            <Chrome className="w-12 h-12 text-amber-400" />
          </div>

          {/* Extension Error Message */}
          <h1 className="text-3xl font-bold text-white mb-4">
            Browser Extension Conflict
          </h1>
          <p className="text-slate-400 mb-6 text-lg">
            {getBrowserExtensionErrorMessage()}
          </p>

          {/* Helpful Tips */}
          <div className="mb-8 p-4 bg-slate-800/50 rounded-lg text-left border border-slate-700">
            <h3 className="text-white font-medium mb-3">Try these solutions:</h3>
            <ul className="text-slate-400 text-sm space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-amber-400 mt-0.5">1.</span>
                <span>Open this page in <strong>Incognito/Private mode</strong></span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-400 mt-0.5">2.</span>
                <span>Disable translation extensions (Google Translate, etc.)</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-400 mt-0.5">3.</span>
                <span>Disable ad blockers temporarily on this site</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-400 mt-0.5">4.</span>
                <span>Try a different browser</span>
              </li>
            </ul>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button
              onClick={() => reset()}
              className="bg-purple-600 hover:bg-purple-700"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Try Again
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
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-4">
      <div className="max-w-lg w-full text-center">
        {/* Error Icon */}
        <div className="w-24 h-24 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-8">
          <AlertTriangle className="w-12 h-12 text-red-400" />
        </div>

        {/* Error Message */}
        <h1 className="text-3xl font-bold text-white mb-4">
          Something went wrong
        </h1>
        <p className="text-slate-400 mb-8 text-lg">
          We apologize for the inconvenience. An unexpected error has occurred.
          Please try again or return to the home page.
        </p>

        {/* Error Details (Development Only) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mb-8 p-4 bg-slate-800/50 rounded-lg text-left border border-slate-700">
            <p className="text-red-400 font-mono text-sm break-all">
              {error.message}
            </p>
            {error.digest && (
              <p className="text-slate-500 font-mono text-xs mt-2">
                Error ID: {error.digest}
              </p>
            )}
          </div>
        )}

        {/* Production Error ID */}
        {process.env.NODE_ENV === 'production' && error.digest && (
          <p className="text-slate-600 text-xs font-mono mb-6">
            Reference: {error.digest}
          </p>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Button
            onClick={() => reset()}
            className="bg-purple-600 hover:bg-purple-700"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Try Again
          </Button>
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

        {/* Support Link */}
        <p className="mt-8 text-slate-500 text-sm">
          If this problem persists, please{' '}
          <a href="mailto:support@actorhub.ai" className="text-purple-400 hover:text-purple-300 underline">
            contact support
          </a>
        </p>
      </div>
    </div>
  )
}

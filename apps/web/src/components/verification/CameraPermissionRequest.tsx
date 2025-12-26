'use client'

import { Camera, AlertCircle, RefreshCw, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { CameraError, getCameraErrorMessage } from '@/hooks/useCamera'

interface CameraPermissionRequestProps {
  onRequestPermission: () => void
  isLoading?: boolean
  error?: CameraError | null
  className?: string
}

export function CameraPermissionRequest({
  onRequestPermission,
  isLoading = false,
  error,
  className,
}: CameraPermissionRequestProps) {
  const hasError = error !== null && error !== undefined

  return (
    <div className={cn(
      'flex flex-col items-center justify-center p-8 rounded-lg',
      'bg-gray-800/50 border border-gray-700',
      className
    )}>
      {/* Icon */}
      <div className={cn(
        'w-16 h-16 rounded-full flex items-center justify-center mb-6',
        hasError ? 'bg-red-500/20' : 'bg-blue-500/20'
      )}>
        {hasError ? (
          <AlertCircle className="w-8 h-8 text-red-400" />
        ) : (
          <Camera className="w-8 h-8 text-blue-400" />
        )}
      </div>

      {/* Title */}
      <h3 className="text-xl font-semibold text-white mb-2">
        {hasError ? 'Camera Access Issue' : 'Camera Access Required'}
      </h3>

      {/* Description */}
      <p className="text-gray-400 text-center mb-6 max-w-md">
        {hasError
          ? getCameraErrorMessage(error)
          : 'To verify your identity, we need to access your camera for a live selfie. This ensures you are really you.'}
      </p>

      {/* Action button */}
      {error === 'permission-denied' ? (
        <div className="flex flex-col items-center gap-3">
          <Button
            onClick={onRequestPermission}
            disabled={isLoading}
            variant="outline"
          >
            <RefreshCw className={cn('w-4 h-4 mr-2', isLoading && 'animate-spin')} />
            Try Again
          </Button>
          <p className="text-sm text-gray-500 flex items-center gap-2">
            <Settings className="w-4 h-4" />
            You may need to enable camera in browser settings
          </p>
        </div>
      ) : error === 'not-found' || error === 'not-supported' ? (
        <p className="text-sm text-yellow-500">
          Camera verification is required. Please use a device with a camera.
        </p>
      ) : (
        <Button
          onClick={onRequestPermission}
          disabled={isLoading}
          variant="gradient"
          size="lg"
        >
          {isLoading ? (
            <>
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              Requesting Access...
            </>
          ) : (
            <>
              <Camera className="w-4 h-4 mr-2" />
              Enable Camera
            </>
          )}
        </Button>
      )}

      {/* Privacy note */}
      <p className="text-xs text-gray-500 mt-6 text-center max-w-sm">
        Your selfie is only used for verification and is not stored permanently.
        We take your privacy seriously.
      </p>
    </div>
  )
}

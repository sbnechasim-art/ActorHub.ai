'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Camera, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useCamera, CameraError } from '@/hooks/useCamera'
import { useLivenessDetection } from '@/hooks/useLivenessDetection'
import { captureFrame, generateLivenessMetadata } from '@/lib/camera'
import { CameraPreviewWithRef } from './CameraPreview'
import { CameraPermissionRequest } from './CameraPermissionRequest'
import { CaptureConfirmation } from './CaptureConfirmation'
import { FaceGuideOverlay } from './FaceGuideOverlay'

export type CameraState =
  | 'initial'
  | 'requesting-permission'
  | 'permission-denied'
  | 'camera-not-found'
  | 'preview'
  | 'countdown'
  | 'capturing'
  | 'liveness-check'
  | 'confirming'
  | 'error'

export interface LivenessMetadata {
  captureTimestamp: number
  frameCount: number
  deviceType: 'mobile' | 'desktop'
  cameraFacing: 'user'
}

export interface LiveSelfieCaptureProps {
  onCapture: (imageBlob: Blob, imageBase64: string, livenessMetadata: LivenessMetadata) => void
  onError: (error: CameraError) => void
  onCancel: () => void
  enableLivenessCheck?: boolean
  className?: string
}

export function LiveSelfieCapture({
  onCapture,
  onError,
  onCancel,
  enableLivenessCheck = true,
  className,
}: LiveSelfieCaptureProps) {
  const [state, setState] = useState<CameraState>('initial')
  const [countdown, setCountdown] = useState(3)
  const [capturedImage, setCapturedImage] = useState<{ blob: Blob; base64: string } | null>(null)
  const [livenessMetadata, setLivenessMetadata] = useState<LivenessMetadata | null>(null)

  const videoRef = useRef<HTMLVideoElement>(null)
  const countdownRef = useRef<NodeJS.Timeout | null>(null)

  const { stream, error, isLoading, startCamera, stopCamera } = useCamera()
  const { captureWithLiveness, isChecking } = useLivenessDetection()

  // Handle camera errors
  useEffect(() => {
    if (error) {
      if (error === 'permission-denied') {
        setState('permission-denied')
      } else if (error === 'not-found') {
        setState('camera-not-found')
      } else {
        setState('error')
      }
      onError(error)
    }
  }, [error, onError])

  // Update state when stream is available
  useEffect(() => {
    if (stream && state === 'requesting-permission') {
      setState('preview')
    }
  }, [stream, state])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCamera()
      if (countdownRef.current) {
        clearInterval(countdownRef.current)
      }
    }
  }, [stopCamera])

  const handleRequestPermission = useCallback(async () => {
    setState('requesting-permission')
    await startCamera()
  }, [startCamera])

  const startCountdown = useCallback(() => {
    setState('countdown')
    setCountdown(3)

    countdownRef.current = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          if (countdownRef.current) {
            clearInterval(countdownRef.current)
          }
          handleCapture()
          return 0
        }
        return prev - 1
      })
    }, 1000)
  }, [])

  const handleCapture = useCallback(async () => {
    if (!videoRef.current) return

    setState('capturing')

    try {
      if (enableLivenessCheck) {
        setState('liveness-check')

        const { blob, base64, liveness } = await captureWithLiveness(videoRef.current)

        const metadata = generateLivenessMetadata(liveness.frameCount)
        setLivenessMetadata(metadata)
        setCapturedImage({ blob, base64 })
        setState('confirming')
      } else {
        // Simple capture without liveness
        const { blob, base64 } = await captureFrame(videoRef.current)
        const metadata = generateLivenessMetadata(1)
        setLivenessMetadata(metadata)
        setCapturedImage({ blob, base64 })
        setState('confirming')
      }
    } catch (err) {
      console.error('Capture failed:', err)
      setState('error')
    }
  }, [enableLivenessCheck, captureWithLiveness])

  const handleRetake = useCallback(() => {
    setCapturedImage(null)
    setLivenessMetadata(null)
    setState('preview')
  }, [])

  const handleConfirm = useCallback(() => {
    if (capturedImage && livenessMetadata) {
      stopCamera()
      onCapture(capturedImage.blob, capturedImage.base64, livenessMetadata)
    }
  }, [capturedImage, livenessMetadata, onCapture, stopCamera])

  const handleCancel = useCallback(() => {
    stopCamera()
    onCancel()
  }, [stopCamera, onCancel])

  return (
    <div className={cn('relative', className)}>
      <AnimatePresence mode="wait">
        {/* Initial / Permission Request State */}
        {(state === 'initial' || state === 'requesting-permission' || state === 'permission-denied' || state === 'camera-not-found' || state === 'error') && (
          <motion.div
            key="permission"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <CameraPermissionRequest
              onRequestPermission={handleRequestPermission}
              isLoading={isLoading}
              error={error}
            />
            <Button
              variant="ghost"
              className="mt-4 w-full"
              onClick={handleCancel}
            >
              Cancel
            </Button>
          </motion.div>
        )}

        {/* Camera Preview State */}
        {(state === 'preview' || state === 'countdown' || state === 'capturing' || state === 'liveness-check') && (
          <motion.div
            key="preview"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="flex flex-col"
          >
            {/* Camera view */}
            <div className="relative aspect-[4/3] rounded-lg overflow-hidden bg-black">
              <CameraPreviewWithRef
                stream={stream}
                videoRef={videoRef}
                showGuide={state === 'preview'}
                className="w-full h-full"
              />

              {/* Countdown overlay */}
              {state === 'countdown' && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/40">
                  <motion.div
                    key={countdown}
                    initial={{ scale: 0.5, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 1.5, opacity: 0 }}
                    className="text-8xl font-bold text-white"
                  >
                    {countdown}
                  </motion.div>
                </div>
              )}

              {/* Liveness check overlay */}
              {(state === 'liveness-check' || state === 'capturing') && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/40">
                  <div className="text-center">
                    <div className="w-12 h-12 border-4 border-white border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                    <p className="text-white font-medium">
                      {state === 'liveness-check' ? 'Verifying liveness...' : 'Capturing...'}
                    </p>
                    <p className="text-gray-300 text-sm mt-2">Hold still</p>
                  </div>
                </div>
              )}

              {/* Close button */}
              <button
                onClick={handleCancel}
                className="absolute top-4 right-4 p-2 rounded-full bg-black/40 hover:bg-black/60 text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Capture button */}
            {state === 'preview' && (
              <div className="mt-6 flex justify-center">
                <button
                  onClick={startCountdown}
                  className="w-20 h-20 rounded-full bg-white hover:bg-gray-100 transition-colors flex items-center justify-center shadow-lg"
                >
                  <div className="w-16 h-16 rounded-full border-4 border-gray-300 flex items-center justify-center">
                    <Camera className="w-8 h-8 text-gray-700" />
                  </div>
                </button>
              </div>
            )}

            <p className="text-center text-gray-400 text-sm mt-4">
              Position your face in the oval and tap to capture
            </p>
          </motion.div>
        )}

        {/* Confirmation State */}
        {state === 'confirming' && capturedImage && (
          <motion.div
            key="confirm"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
          >
            <CaptureConfirmation
              imageBlob={capturedImage.blob}
              onConfirm={handleConfirm}
              onRetake={handleRetake}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { logger } from '@/lib/logger'

export type CameraError =
  | 'permission-denied'
  | 'not-found'
  | 'in-use'
  | 'not-supported'
  | 'unknown'

export interface CameraState {
  stream: MediaStream | null
  error: CameraError | null
  isLoading: boolean
  isActive: boolean
}

interface UseCameraOptions {
  facingMode?: 'user' | 'environment'
  width?: number
  height?: number
}

const defaultOptions: UseCameraOptions = {
  facingMode: 'user',
  width: 1280,
  height: 720,
}

export function useCamera(options: UseCameraOptions = {}) {
  const opts = { ...defaultOptions, ...options }
  const [state, setState] = useState<CameraState>({
    stream: null,
    error: null,
    isLoading: false,
    isActive: false,
  })

  const streamRef = useRef<MediaStream | null>(null)

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => {
        track.stop()
      })
      streamRef.current = null
    }
    setState({
      stream: null,
      error: null,
      isLoading: false,
      isActive: false,
    })
  }, [])

  const startCamera = useCallback(async () => {
    // Check if getUserMedia is supported
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setState(prev => ({
        ...prev,
        error: 'not-supported',
        isLoading: false,
      }))
      return false
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }))

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: opts.facingMode,
          width: { ideal: opts.width },
          height: { ideal: opts.height },
        },
        audio: false,
      })

      streamRef.current = stream
      setState({
        stream,
        error: null,
        isLoading: false,
        isActive: true,
      })

      logger.info('Camera started successfully')
      return true
    } catch (err) {
      const error = err as Error
      let cameraError: CameraError = 'unknown'

      if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        cameraError = 'permission-denied'
      } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
        cameraError = 'not-found'
      } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
        cameraError = 'in-use'
      } else if (error.name === 'OverconstrainedError') {
        // Try again with lower constraints
        try {
          const fallbackStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: opts.facingMode },
            audio: false,
          })
          streamRef.current = fallbackStream
          setState({
            stream: fallbackStream,
            error: null,
            isLoading: false,
            isActive: true,
          })
          logger.info('Camera started with fallback constraints')
          return true
        } catch {
          cameraError = 'unknown'
        }
      }

      logger.error('Camera error', { error: error.name, message: error.message })
      setState({
        stream: null,
        error: cameraError,
        isLoading: false,
        isActive: false,
      })
      return false
    }
  }, [opts.facingMode, opts.width, opts.height])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  return {
    stream: state.stream,
    error: state.error,
    isLoading: state.isLoading,
    isActive: state.isActive,
    startCamera,
    stopCamera,
  }
}

export function getCameraErrorMessage(error: CameraError): string {
  switch (error) {
    case 'permission-denied':
      return 'Camera access was denied. Please enable camera permissions in your browser settings.'
    case 'not-found':
      return 'No camera found. Please connect a webcam or use a device with a camera.'
    case 'in-use':
      return 'Camera is being used by another application. Please close other apps using the camera.'
    case 'not-supported':
      return 'Camera is not supported in this browser. Please use a modern browser like Chrome or Firefox.'
    default:
      return 'An unexpected camera error occurred. Please try again.'
  }
}

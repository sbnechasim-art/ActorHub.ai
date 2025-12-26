'use client'

import { useState, useCallback, useRef } from 'react'
import { captureFrame } from '@/lib/camera'
import { logger } from '@/lib/logger'

interface LivenessResult {
  isLive: boolean
  confidence: number
  frameCount: number
  captureTimestamp: number
}

interface UseLivenessDetectionOptions {
  frameCount?: number
  intervalMs?: number
  movementThreshold?: number
}

const defaultOptions: UseLivenessDetectionOptions = {
  frameCount: 5,
  intervalMs: 400,
  movementThreshold: 0.02, // 2% pixel difference required
}

export function useLivenessDetection(options: UseLivenessDetectionOptions = {}) {
  const opts = { ...defaultOptions, ...options }
  const [isChecking, setIsChecking] = useState(false)
  const [result, setResult] = useState<LivenessResult | null>(null)
  const framesRef = useRef<ImageData[]>([])

  /**
   * Capture multiple frames and check for movement/liveness
   */
  const checkLiveness = useCallback(async (
    videoElement: HTMLVideoElement
  ): Promise<LivenessResult> => {
    setIsChecking(true)
    framesRef.current = []

    try {
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d', { willReadFrequently: true })

      if (!ctx) {
        throw new Error('Could not get canvas context')
      }

      // Set canvas size to video size (smaller for faster processing)
      const width = 320
      const height = 240
      canvas.width = width
      canvas.height = height

      // Capture frames
      const frames: ImageData[] = []
      for (let i = 0; i < opts.frameCount!; i++) {
        ctx.drawImage(videoElement, 0, 0, width, height)
        const imageData = ctx.getImageData(0, 0, width, height)
        frames.push(imageData)

        if (i < opts.frameCount! - 1) {
          await delay(opts.intervalMs!)
        }
      }

      framesRef.current = frames

      // Analyze frames for movement
      const movementScore = analyzeFrameMovement(frames)
      const isLive = movementScore > opts.movementThreshold!

      const livenessResult: LivenessResult = {
        isLive,
        confidence: Math.min(movementScore / (opts.movementThreshold! * 2), 1),
        frameCount: frames.length,
        captureTimestamp: Date.now(),
      }

      logger.info('Liveness check completed', { isLive, movementScore })
      setResult(livenessResult)
      setIsChecking(false)

      return livenessResult
    } catch (err) {
      logger.error('Liveness check failed', err)
      setIsChecking(false)

      const failedResult: LivenessResult = {
        isLive: false,
        confidence: 0,
        frameCount: 0,
        captureTimestamp: Date.now(),
      }
      setResult(failedResult)
      return failedResult
    }
  }, [opts.frameCount, opts.intervalMs, opts.movementThreshold])

  /**
   * Quick capture with liveness - returns the best frame
   */
  const captureWithLiveness = useCallback(async (
    videoElement: HTMLVideoElement
  ): Promise<{
    blob: Blob
    base64: string
    liveness: LivenessResult
  }> => {
    // First, run liveness check
    const livenessResult = await checkLiveness(videoElement)

    // Then capture the final frame
    const { blob, base64 } = await captureFrame(videoElement)

    return {
      blob,
      base64,
      liveness: livenessResult,
    }
  }, [checkLiveness])

  const reset = useCallback(() => {
    setResult(null)
    framesRef.current = []
  }, [])

  return {
    checkLiveness,
    captureWithLiveness,
    isChecking,
    result,
    reset,
  }
}

/**
 * Analyze movement between frames by comparing pixel differences
 */
function analyzeFrameMovement(frames: ImageData[]): number {
  if (frames.length < 2) return 0

  let totalDifference = 0
  let comparisons = 0

  // Compare consecutive frames
  for (let i = 1; i < frames.length; i++) {
    const diff = compareFrames(frames[i - 1], frames[i])
    totalDifference += diff
    comparisons++
  }

  // Also compare first and last frame (should show more movement)
  const firstLastDiff = compareFrames(frames[0], frames[frames.length - 1])
  totalDifference += firstLastDiff
  comparisons++

  return totalDifference / comparisons
}

/**
 * Compare two frames and return a difference score (0-1)
 */
function compareFrames(frame1: ImageData, frame2: ImageData): number {
  const data1 = frame1.data
  const data2 = frame2.data

  if (data1.length !== data2.length) return 0

  let differentPixels = 0
  const threshold = 30 // RGB difference threshold to count as "different"

  // Sample every 4th pixel for performance (still accurate enough)
  for (let i = 0; i < data1.length; i += 16) {
    const rDiff = Math.abs(data1[i] - data2[i])
    const gDiff = Math.abs(data1[i + 1] - data2[i + 1])
    const bDiff = Math.abs(data1[i + 2] - data2[i + 2])

    if (rDiff + gDiff + bDiff > threshold * 3) {
      differentPixels++
    }
  }

  const totalSampledPixels = data1.length / 16
  return differentPixels / totalSampledPixels
}

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

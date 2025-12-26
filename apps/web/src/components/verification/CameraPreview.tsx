'use client'

import { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'
import { FaceGuideOverlay } from './FaceGuideOverlay'

interface CameraPreviewProps {
  stream: MediaStream | null
  showGuide?: boolean
  isPositioned?: boolean
  className?: string
  mirrored?: boolean
}

export function CameraPreview({
  stream,
  showGuide = true,
  isPositioned = false,
  className,
  mirrored = true,
}: CameraPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    const video = videoRef.current
    if (!video || !stream) return

    video.srcObject = stream

    // Handle autoplay
    const playVideo = async () => {
      try {
        await video.play()
      } catch (err) {
        // Autoplay might be blocked, that's okay - user will see the frame
        console.warn('Video autoplay blocked:', err)
      }
    }

    playVideo()

    return () => {
      video.srcObject = null
    }
  }, [stream])

  return (
    <div className={cn('relative overflow-hidden rounded-lg bg-black', className)}>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className={cn(
          'w-full h-full object-cover',
          mirrored && 'scale-x-[-1]'
        )}
      />

      {showGuide && <FaceGuideOverlay isPositioned={isPositioned} />}

      {/* Loading state when no stream */}
      {!stream && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
          <div className="text-center text-gray-400">
            <div className="w-12 h-12 border-4 border-gray-600 border-t-blue-500 rounded-full animate-spin mx-auto mb-4" />
            <p>Starting camera...</p>
          </div>
        </div>
      )}
    </div>
  )
}

// Expose ref for capturing frames
export function CameraPreviewWithRef({
  stream,
  showGuide = true,
  isPositioned = false,
  className,
  mirrored = true,
  videoRef,
}: CameraPreviewProps & { videoRef: React.RefObject<HTMLVideoElement | null> }) {
  useEffect(() => {
    const video = videoRef.current
    if (!video || !stream) return

    video.srcObject = stream

    const playVideo = async () => {
      try {
        await video.play()
      } catch (err) {
        console.warn('Video autoplay blocked:', err)
      }
    }

    playVideo()

    return () => {
      if (video) {
        video.srcObject = null
      }
    }
  }, [stream, videoRef])

  return (
    <div className={cn('relative overflow-hidden rounded-lg bg-black', className)}>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className={cn(
          'w-full h-full object-cover',
          mirrored && 'scale-x-[-1]'
        )}
      />

      {showGuide && <FaceGuideOverlay isPositioned={isPositioned} />}

      {!stream && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
          <div className="text-center text-gray-400">
            <div className="w-12 h-12 border-4 border-gray-600 border-t-blue-500 rounded-full animate-spin mx-auto mb-4" />
            <p>Starting camera...</p>
          </div>
        </div>
      )}
    </div>
  )
}

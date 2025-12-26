/**
 * Camera utilities for selfie capture
 */

export interface CaptureOptions {
  quality?: number  // 0-1, default 0.9
  format?: 'image/jpeg' | 'image/png'
  maxWidth?: number
  maxHeight?: number
}

const defaultCaptureOptions: CaptureOptions = {
  quality: 0.9,
  format: 'image/jpeg',
  maxWidth: 1280,
  maxHeight: 720,
}

/**
 * Capture a frame from a video element
 */
export async function captureFrame(
  video: HTMLVideoElement,
  options: CaptureOptions = {}
): Promise<{ blob: Blob; base64: string }> {
  const opts = { ...defaultCaptureOptions, ...options }

  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')

  if (!ctx) {
    throw new Error('Could not get canvas context')
  }

  // Calculate dimensions maintaining aspect ratio
  let width = video.videoWidth
  let height = video.videoHeight

  if (opts.maxWidth && width > opts.maxWidth) {
    const ratio = opts.maxWidth / width
    width = opts.maxWidth
    height = Math.round(height * ratio)
  }

  if (opts.maxHeight && height > opts.maxHeight) {
    const ratio = opts.maxHeight / height
    height = opts.maxHeight
    width = Math.round(width * ratio)
  }

  canvas.width = width
  canvas.height = height

  // Mirror the image (since we show mirrored preview)
  ctx.translate(width, 0)
  ctx.scale(-1, 1)
  ctx.drawImage(video, 0, 0, width, height)

  // Convert to blob
  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (b) => {
        if (b) resolve(b)
        else reject(new Error('Failed to create blob'))
      },
      opts.format,
      opts.quality
    )
  })

  // Convert to base64
  const base64 = await blobToBase64(blob)

  return { blob, base64 }
}

/**
 * Capture multiple frames for liveness detection
 */
export async function captureMultipleFrames(
  video: HTMLVideoElement,
  frameCount: number = 5,
  intervalMs: number = 400
): Promise<Array<{ blob: Blob; timestamp: number }>> {
  const frames: Array<{ blob: Blob; timestamp: number }> = []

  for (let i = 0; i < frameCount; i++) {
    const { blob } = await captureFrame(video)
    frames.push({
      blob,
      timestamp: Date.now(),
    })

    if (i < frameCount - 1) {
      await delay(intervalMs)
    }
  }

  return frames
}

/**
 * Convert blob to base64 string
 */
export function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => {
      if (typeof reader.result === 'string') {
        // Remove data URL prefix (e.g., "data:image/jpeg;base64,")
        const base64 = reader.result.split(',')[1]
        resolve(base64)
      } else {
        reject(new Error('Failed to convert to base64'))
      }
    }
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

/**
 * Convert base64 to blob
 */
export function base64ToBlob(base64: string, mimeType: string = 'image/jpeg'): Blob {
  const byteString = atob(base64)
  const ab = new ArrayBuffer(byteString.length)
  const ia = new Uint8Array(ab)

  for (let i = 0; i < byteString.length; i++) {
    ia[i] = byteString.charCodeAt(i)
  }

  return new Blob([ab], { type: mimeType })
}

/**
 * Check if camera is supported in current browser
 */
export function isCameraSupported(): boolean {
  return !!(
    navigator.mediaDevices &&
    navigator.mediaDevices.getUserMedia
  )
}

/**
 * Check if we're in a secure context (required for camera)
 */
export function isSecureContext(): boolean {
  return window.isSecureContext
}

/**
 * Get list of available cameras
 */
export async function getCameraList(): Promise<MediaDeviceInfo[]> {
  if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
    return []
  }

  const devices = await navigator.mediaDevices.enumerateDevices()
  return devices.filter(device => device.kind === 'videoinput')
}

/**
 * Detect device type
 */
export function getDeviceType(): 'mobile' | 'desktop' {
  const userAgent = navigator.userAgent.toLowerCase()
  const isMobile = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent)
  return isMobile ? 'mobile' : 'desktop'
}

/**
 * Create object URL for blob (with cleanup helper)
 */
export function createImageUrl(blob: Blob): string {
  return URL.createObjectURL(blob)
}

/**
 * Revoke object URL to free memory
 */
export function revokeImageUrl(url: string): void {
  URL.revokeObjectURL(url)
}

/**
 * Utility delay function
 */
function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Generate liveness metadata
 */
export function generateLivenessMetadata(frameCount: number): {
  captureTimestamp: number
  frameCount: number
  deviceType: 'mobile' | 'desktop'
  cameraFacing: 'user'
} {
  return {
    captureTimestamp: Date.now(),
    frameCount,
    deviceType: getDeviceType(),
    cameraFacing: 'user',
  }
}

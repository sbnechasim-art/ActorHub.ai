/**
 * Custom Image Loader for CDN
 * Used when NEXT_PUBLIC_CDN_URL is set in production
 */

interface ImageLoaderProps {
  src: string
  width: number
  quality?: number
}

export default function imageLoader({ src, width, quality }: ImageLoaderProps): string {
  const cdnUrl = process.env.NEXT_PUBLIC_CDN_URL

  // If no CDN URL configured, return original source
  if (!cdnUrl) {
    return src
  }

  // Handle absolute URLs (external images)
  if (src.startsWith('http://') || src.startsWith('https://')) {
    return src
  }

  // Handle relative paths - serve from CDN
  const q = quality || 75

  // If using Cloudflare or similar CDN with image resizing
  // Adjust the URL format based on your CDN provider
  const params = new URLSearchParams({
    url: src,
    w: width.toString(),
    q: q.toString(),
  })

  // For CloudFront with Lambda@Edge or Cloudflare Images
  // return `${cdnUrl}/cdn-cgi/image/width=${width},quality=${q}${src}`

  // For standard CDN (just serve static files)
  return `${cdnUrl}${src}`
}

/**
 * Helper to get optimized image URL
 */
export function getOptimizedImageUrl(
  src: string,
  options?: { width?: number; height?: number; quality?: number }
): string {
  const cdnUrl = process.env.NEXT_PUBLIC_CDN_URL

  if (!cdnUrl || src.startsWith('http')) {
    return src
  }

  const width = options?.width || 800
  const quality = options?.quality || 75

  return imageLoader({ src, width, quality })
}

/**
 * Get static asset URL (for non-image assets like fonts, etc.)
 */
export function getAssetUrl(path: string): string {
  const cdnUrl = process.env.NEXT_PUBLIC_CDN_URL

  if (!cdnUrl || path.startsWith('http')) {
    return path
  }

  return `${cdnUrl}${path.startsWith('/') ? path : `/${path}`}`
}

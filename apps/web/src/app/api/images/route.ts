import { NextRequest, NextResponse } from 'next/server'

// Strict allowlist of exact hostnames (no wildcard subdomains for security)
const ALLOWED_HOSTS = new Set([
  'localhost',
  '127.0.0.1',
  'actorhub-uploads.s3.amazonaws.com',
  'actorhub-uploads.s3.us-east-1.amazonaws.com',
  'actorhub-actor-packs.s3.amazonaws.com',
  'actorhub-actor-packs.s3.us-east-1.amazonaws.com',
])

// Allowed ports for localhost (MinIO)
const ALLOWED_LOCALHOST_PORTS = new Set([9000, 9001])

// Max URL length to prevent DoS
const MAX_URL_LENGTH = 2048

/**
 * Image proxy route - proxies images from MinIO/S3 to avoid CORS issues
 * Security: Strict hostname allowlist, port validation, URL length limit
 */
export async function GET(request: NextRequest) {
  const url = request.nextUrl.searchParams.get('url')

  if (!url) {
    return NextResponse.json({ error: 'Missing url parameter' }, { status: 400 })
  }

  // Validate URL length to prevent DoS
  if (url.length > MAX_URL_LENGTH) {
    return NextResponse.json({ error: 'URL too long' }, { status: 400 })
  }

  try {
    const parsedUrl = new URL(url)

    // Only allow http/https protocols
    if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
      return NextResponse.json({ error: 'Invalid protocol' }, { status: 400 })
    }

    // Check if hostname is in strict allowlist (exact match only)
    if (!ALLOWED_HOSTS.has(parsedUrl.hostname)) {
      return NextResponse.json({ error: 'URL not allowed' }, { status: 403 })
    }

    // For localhost, validate port to prevent SSRF to other local services
    if (parsedUrl.hostname === 'localhost' || parsedUrl.hostname === '127.0.0.1') {
      const port = parsedUrl.port ? parseInt(parsedUrl.port) : 80
      if (!ALLOWED_LOCALHOST_PORTS.has(port)) {
        return NextResponse.json({ error: 'Port not allowed' }, { status: 403 })
      }
    }

    // Rewrite localhost URLs to use backend MinIO
    let fetchUrl = url
    if (parsedUrl.hostname === 'localhost' || parsedUrl.hostname === '127.0.0.1') {
      fetchUrl = url.replace(parsedUrl.origin, process.env.MINIO_URL || 'http://localhost:9000')
    }

    // Fetch with timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 10000)

    const response = await fetch(fetchUrl, {
      signal: controller.signal,
      headers: {
        ...(request.headers.get('range') ? { 'Range': request.headers.get('range')! } : {}),
      },
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      return NextResponse.json(
        { error: `Failed to fetch image: ${response.status}` },
        { status: response.status }
      )
    }

    const contentType = response.headers.get('content-type') || 'image/jpeg'
    
    // Validate content type is an image
    if (!contentType.startsWith('image/')) {
      return NextResponse.json({ error: 'Not an image' }, { status: 400 })
    }

    const contentLength = response.headers.get('content-length')
    const imageData = await response.arrayBuffer()

    return new NextResponse(imageData, {
      status: response.status,
      headers: {
        'Content-Type': contentType,
        ...(contentLength ? { 'Content-Length': contentLength } : {}),
        'Cache-Control': 'public, max-age=86400, immutable',
        'X-Content-Type-Options': 'nosniff',
      },
    })
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json({ error: 'Request timeout' }, { status: 504 })
    }
    console.error('Image proxy error:', error)
    return NextResponse.json({ error: 'Failed to proxy image' }, { status: 500 })
  }
}

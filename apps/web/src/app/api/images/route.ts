import { NextRequest, NextResponse } from 'next/server'

/**
 * Image proxy route - proxies images from MinIO/S3 to avoid CORS issues
 * and make localhost URLs work from any client machine.
 *
 * Usage: /api/images?url=http://localhost:9000/bucket/path/to/image.jpg
 */
export async function GET(request: NextRequest) {
  const url = request.nextUrl.searchParams.get('url')

  if (!url) {
    return NextResponse.json({ error: 'Missing url parameter' }, { status: 400 })
  }

  try {
    // Parse and validate the URL
    const parsedUrl = new URL(url)

    // Only allow proxying from localhost (MinIO) or our S3 buckets
    const allowedHosts = [
      'localhost',
      '127.0.0.1',
      's3.amazonaws.com',
      'actorhub-uploads.s3.amazonaws.com',
      'actorhub-actor-packs.s3.amazonaws.com',
    ]

    const isAllowed = allowedHosts.some(host =>
      parsedUrl.hostname === host ||
      parsedUrl.hostname.endsWith('.' + host)
    )

    if (!isAllowed) {
      return NextResponse.json({ error: 'URL not allowed' }, { status: 403 })
    }

    // For localhost URLs, rewrite to use the backend MinIO URL
    let fetchUrl = url
    if (parsedUrl.hostname === 'localhost' || parsedUrl.hostname === '127.0.0.1') {
      // Use the backend URL - the Next.js server can access localhost:9000
      fetchUrl = url.replace(parsedUrl.origin, process.env.MINIO_URL || 'http://localhost:9000')
    }

    // Fetch the image from MinIO/S3
    const response = await fetch(fetchUrl, {
      headers: {
        // Forward any range headers for partial content
        ...(request.headers.get('range') ? { 'Range': request.headers.get('range')! } : {}),
      },
    })

    if (!response.ok) {
      return NextResponse.json(
        { error: `Failed to fetch image: ${response.status}` },
        { status: response.status }
      )
    }

    // Get the content type from the response
    const contentType = response.headers.get('content-type') || 'image/jpeg'
    const contentLength = response.headers.get('content-length')

    // Stream the image back to the client
    const imageData = await response.arrayBuffer()

    return new NextResponse(imageData, {
      status: response.status,
      headers: {
        'Content-Type': contentType,
        ...(contentLength ? { 'Content-Length': contentLength } : {}),
        // Cache for 1 day
        'Cache-Control': 'public, max-age=86400, immutable',
      },
    })
  } catch (error) {
    console.error('Image proxy error:', error)
    return NextResponse.json(
      { error: 'Failed to proxy image' },
      { status: 500 }
    )
  }
}

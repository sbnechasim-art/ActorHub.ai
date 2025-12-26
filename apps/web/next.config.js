/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Required for Docker standalone build
  output: 'standalone',

  // Performance: Enable SWC minification
  swcMinify: true,

  // Performance: Compress responses
  compress: true,

  // Performance: Generate ETags for caching
  generateEtags: true,

  // CDN Configuration for production
  // Set NEXT_PUBLIC_CDN_URL in production (e.g., https://cdn.actorhub.ai)
  assetPrefix: process.env.NEXT_PUBLIC_CDN_URL || '',

  // Performance: Enable experimental features
  experimental: {
    // Optimize package imports for smaller bundles
    optimizePackageImports: ['lucide-react', '@radix-ui/react-icons'],
  },

  images: {
    // CDN loader for images in production
    loader: process.env.NEXT_PUBLIC_CDN_URL ? 'custom' : 'default',
    loaderFile: process.env.NEXT_PUBLIC_CDN_URL ? './src/lib/imageLoader.ts' : undefined,
    remotePatterns: [
      { protocol: 'http', hostname: 'localhost' },
      { protocol: 'https', hostname: 'actorhub.ai' },
      { protocol: 'https', hostname: 'www.actorhub.ai' },
      { protocol: 'https', hostname: 'api.actorhub.ai' },
      { protocol: 'https', hostname: 'cdn.actorhub.ai' },
      { protocol: 'https', hostname: 'images.unsplash.com' },
      { protocol: 'https', hostname: 'randomuser.me' },
      // S3/MinIO CDN origins
      { protocol: 'https', hostname: '*.s3.amazonaws.com' },
      { protocol: 'https', hostname: '*.cloudfront.net' },
    ],
    // Optimize image loading
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    // Cache optimized images for 60 days
    minimumCacheTTL: 60 * 60 * 24 * 60,
  },

  // Headers for security and caching
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          // Security headers
          { key: 'X-DNS-Prefetch-Control', value: 'on' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'origin-when-cross-origin' },
        ],
      },
      {
        // Cache static assets
        source: '/static/:path*',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
    ]
  },

  async rewrites() {
    // Backend API URL (not the public one which may be relative)
    const BACKEND_URL = process.env.BACKEND_API_URL || 'http://localhost:8000'
    return [
      {
        source: '/api/v1/:path*',
        destination: `${BACKEND_URL}/api/v1/:path*`,
      },
    ]
  },
}

module.exports = nextConfig

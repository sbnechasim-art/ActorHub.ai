import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(amount: number, currency = 'USD') {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(amount)
}

export function formatNumber(num: number) {
  return new Intl.NumberFormat('en-US').format(num)
}

export function formatDate(date: string | Date) {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(date))
}

export function formatRelativeTime(date: string | Date) {
  const now = new Date()
  const then = new Date(date)
  const diffMs = now.getTime() - then.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`
  return `${Math.floor(diffDays / 365)} years ago`
}

export function truncate(str: string, length: number) {
  if (str.length <= length) return str
  return str.slice(0, length) + '...'
}

export function getInitials(name: string) {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

/**
 * Convert MinIO/S3 image URLs to proxied URLs that work from any client.
 * This handles localhost URLs that wouldn't be accessible from remote browsers.
 *
 * @param url The original image URL (e.g., http://localhost:9000/bucket/image.jpg)
 * @returns Proxied URL through the Next.js API or the original URL if already accessible
 */
export function getProxiedImageUrl(url: string | null | undefined): string | undefined {
  if (!url) return undefined

  // If it's already an external URL (like Unsplash), return as-is
  if (
    url.startsWith('https://images.unsplash.com') ||
    url.startsWith('https://randomuser.me') ||
    url.startsWith('data:')
  ) {
    return url
  }

  // If it's a localhost/127.0.0.1 URL, proxy it through our API
  if (url.includes('localhost') || url.includes('127.0.0.1')) {
    return `/api/images?url=${encodeURIComponent(url)}`
  }

  // For other URLs (like production S3), return as-is
  return url
}

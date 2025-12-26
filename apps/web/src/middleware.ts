import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Routes that require authentication
const PROTECTED_ROUTES = [
  '/dashboard',
  '/settings',
  '/identity/create',
  '/identity/register',
  '/checkout',
  '/admin',
]

// Routes that should redirect to dashboard if already authenticated
const AUTH_ROUTES = [
  '/sign-in',
  '/sign-up',
]

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Get auth token from cookie (httpOnly cookie set by backend)
  const accessToken = request.cookies.get('access_token')?.value
  const isAuthenticated = !!accessToken

  // Check if current path matches protected routes
  const isProtectedRoute = PROTECTED_ROUTES.some(route =>
    pathname === route || pathname.startsWith(`${route}/`)
  )

  // Check if current path is an auth route
  const isAuthRoute = AUTH_ROUTES.some(route =>
    pathname === route || pathname.startsWith(`${route}/`)
  )

  // Redirect unauthenticated users from protected routes to sign-in
  if (isProtectedRoute && !isAuthenticated) {
    const signInUrl = new URL('/sign-in', request.url)
    signInUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(signInUrl)
  }

  // Redirect authenticated users from auth routes to dashboard
  if (isAuthRoute && isAuthenticated) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)',
  ],
}

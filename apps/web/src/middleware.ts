import { NextResponse } from 'next/server'

// Middleware for route protection
// Protected routes require JWT token in localStorage (checked client-side)
export function middleware() {
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!.+\\.[\\w]+$|_next).*)', '/', '/(api|trpc)(.*)'],
}

import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const code = searchParams.get('code')
  const state = searchParams.get('state')
  const error = searchParams.get('error')

  // Handle OAuth errors
  if (error) {
    const errorDescription = searchParams.get('error_description') || 'Authentication failed'
    return NextResponse.redirect(
      new URL(`/sign-in?error=${encodeURIComponent(errorDescription)}`, request.url)
    )
  }

  if (!code || !state) {
    return NextResponse.redirect(
      new URL('/sign-in?error=Missing+authorization+code', request.url)
    )
  }

  // Forward to backend OAuth callback
  const backendUrl = `${API_URL}/oauth/google/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`

  try {
    const response = await fetch(backendUrl, {
      redirect: 'manual',
    })

    // Backend returns a redirect with cookies
    if (response.status === 302) {
      const location = response.headers.get('location')
      const setCookieHeaders = response.headers.getSetCookie()

      if (location) {
        const redirectResponse = NextResponse.redirect(new URL(location))

        // Forward cookies from backend
        setCookieHeaders.forEach(cookie => {
          redirectResponse.headers.append('Set-Cookie', cookie)
        })

        return redirectResponse
      }
    }

    // Handle error responses
    const errorData = await response.json().catch(() => ({ detail: 'Authentication failed' }))
    return NextResponse.redirect(
      new URL(`/sign-in?error=${encodeURIComponent(errorData.detail || 'Authentication failed')}`, request.url)
    )
  } catch (error) {
    console.error('Google OAuth callback error:', error)
    return NextResponse.redirect(
      new URL('/sign-in?error=Authentication+service+unavailable', request.url)
    )
  }
}

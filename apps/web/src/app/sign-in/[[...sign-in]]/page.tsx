'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { useRouter, useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ArrowLeft, Loader2, Shield, Zap, Lock } from 'lucide-react'
import { Logo } from '@/components/ui/logo'
import { logger } from '@/lib/logger'

// SVG Icons for OAuth providers
function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  )
}

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
    </svg>
  )
}

export default function SignInPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [oauthLoading, setOauthLoading] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [oauthProviders, setOauthProviders] = useState<{google: boolean, github: boolean}>({ google: false, github: false })

  // Check available OAuth providers
  useEffect(() => {
    const checkOAuthProviders = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/oauth/providers`)
        if (response.ok) {
          const data = await response.json()
          const providers: {google: boolean, github: boolean} = { google: false, github: false }
          for (const provider of data.providers) {
            if (provider.id === 'google') providers.google = provider.enabled
            if (provider.id === 'github') providers.github = provider.enabled
          }
          setOauthProviders(providers)
        }
      } catch {
        // OAuth not available
      }
    }
    checkOAuthProviders()
  }, [])

  // Handle OAuth error from URL params
  useEffect(() => {
    const errorParam = searchParams.get('error')
    if (errorParam) {
      setError(decodeURIComponent(errorParam))
    }
    const authSuccess = searchParams.get('auth_success')
    if (authSuccess === 'true') {
      router.push('/dashboard')
    }
  }, [searchParams, router])

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/users/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      })

      if (response.ok) {
        const data = await response.json()

        // Check if 2FA is required
        if (data.requires_2fa) {
          sessionStorage.setItem('2fa_pending_token', data.pending_token)
          router.push('/sign-in/2fa')
          return
        }

        localStorage.setItem('token', data.access_token)
        router.push('/dashboard')
      } else {
        const errorData = await response.json()
        let errorMessage = 'Login failed'
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail
        } else if (errorData.message) {
          errorMessage = errorData.message
        } else if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
          errorMessage = errorData.detail[0].msg || 'Validation error'
        }
        setError(errorMessage)
      }
    } catch (err) {
      logger.error('Sign in connection error', err as Error)
      setError('Connection error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleOAuthLogin = async (provider: 'google' | 'github') => {
    setOauthLoading(provider)
    setError('')

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/oauth/${provider}/authorize`)

      if (response.ok) {
        const data = await response.json()
        window.location.href = data.authorization_url
      } else {
        const errorData = await response.json()
        setError(errorData.detail || `${provider} login is not available`)
        setOauthLoading(null)
      }
    } catch (err) {
      logger.error(`${provider} OAuth error`, err as Error)
      setError(`Unable to connect to ${provider}. Please try again.`)
      setOauthLoading(null)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left Side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900 overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-30">
          <div className="absolute top-0 left-0 w-96 h-96 bg-purple-500/30 rounded-full filter blur-3xl" />
          <div className="absolute bottom-0 right-0 w-96 h-96 bg-blue-500/30 rounded-full filter blur-3xl" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-r from-purple-500/20 to-blue-500/20 rounded-full filter blur-3xl" />
        </div>

        {/* Grid Pattern */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(139,92,246,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(139,92,246,0.03)_1px,transparent_1px)] bg-[size:50px_50px]" />

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-center items-center w-full p-12">
          {/* Large Logo */}
          <div className="mb-8">
            <div className="relative w-56 h-56 mb-3 drop-shadow-[0_0_30px_rgba(59,130,246,0.5)]">
              <Image
                src="/logo.png"
                alt="ActorHub.ai"
                fill
                className="object-contain"
                priority
              />
            </div>
            <h1 className="text-4xl font-bold text-center">
              <span className="bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
                ActorHub
              </span>
              <span className="text-purple-400">.ai</span>
            </h1>
          </div>

          {/* Tagline */}
          <p className="text-xl text-slate-300 text-center max-w-md mb-12">
            Protect your digital identity and monetize your likeness with AI-powered licensing
          </p>

          {/* Features */}
          <div className="space-y-4 w-full max-w-sm">
            <div className="flex items-center gap-4 p-4 bg-white/5 rounded-xl backdrop-blur-sm border border-white/10">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <Shield className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <h3 className="text-white font-medium">Identity Protection</h3>
                <p className="text-sm text-slate-400">AI-powered face recognition</p>
              </div>
            </div>
            <div className="flex items-center gap-4 p-4 bg-white/5 rounded-xl backdrop-blur-sm border border-white/10">
              <div className="p-2 bg-blue-500/20 rounded-lg">
                <Zap className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <h3 className="text-white font-medium">Instant Licensing</h3>
                <p className="text-sm text-slate-400">Monetize your digital presence</p>
              </div>
            </div>
            <div className="flex items-center gap-4 p-4 bg-white/5 rounded-xl backdrop-blur-sm border border-white/10">
              <div className="p-2 bg-green-500/20 rounded-lg">
                <Lock className="w-6 h-6 text-green-400" />
              </div>
              <div>
                <h3 className="text-white font-medium">Secure Platform</h3>
                <p className="text-sm text-slate-400">Enterprise-grade security</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center bg-slate-950 p-6 lg:p-12">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden flex justify-center mb-8">
            <Logo variant="full" size="xl" glow asDiv />
          </div>

          {/* Back Link */}
          <Link
            href="/"
            className="inline-flex items-center text-slate-400 hover:text-white transition mb-8 group"
          >
            <ArrowLeft className="w-4 h-4 mr-2 group-hover:-translate-x-1 transition-transform" />
            Back to home
          </Link>

          {/* Form Card */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8 backdrop-blur-sm">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-white mb-2">Welcome back</h2>
              <p className="text-slate-400">Sign in to continue to ActorHub.ai</p>
            </div>

            {/* OAuth Buttons - only show if providers are enabled */}
            {(oauthProviders.google || oauthProviders.github) && (
              <>
                <div className="space-y-3 mb-6">
                  {oauthProviders.google && (
                    <Button
                      type="button"
                      variant="outline"
                      className="w-full h-12 bg-white hover:bg-gray-100 text-gray-900 border-0 font-medium"
                      onClick={() => handleOAuthLogin('google')}
                      disabled={!!oauthLoading}
                    >
                      {oauthLoading === 'google' ? (
                        <Loader2 className="w-5 h-5 mr-3 animate-spin" />
                      ) : (
                        <GoogleIcon className="w-5 h-5 mr-3" />
                      )}
                      Continue with Google
                    </Button>
                  )}

                  {oauthProviders.github && (
                    <Button
                      type="button"
                      variant="outline"
                      className="w-full h-12 bg-slate-800 hover:bg-slate-700 text-white border-slate-700 font-medium"
                      onClick={() => handleOAuthLogin('github')}
                      disabled={!!oauthLoading}
                    >
                      {oauthLoading === 'github' ? (
                        <Loader2 className="w-5 h-5 mr-3 animate-spin" />
                      ) : (
                        <GitHubIcon className="w-5 h-5 mr-3" />
                      )}
                      Continue with GitHub
                    </Button>
                  )}
                </div>

                {/* Divider */}
                <div className="relative my-8">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-slate-700"></div>
                  </div>
                  <div className="relative flex justify-center">
                    <span className="px-4 bg-slate-900/50 text-sm text-slate-500">or</span>
                  </div>
                </div>
              </>
            )}

            {/* Email/Password Form */}
            <form onSubmit={handleSignIn} className="space-y-5">
              {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm">
                  {error}
                </div>
              )}

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300">Email</label>
                <Input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-12 bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-purple-500 focus:ring-purple-500/20"
                  required
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300">Password</label>
                <Input
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-12 bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-purple-500 focus:ring-purple-500/20"
                  required
                />
              </div>

              <div className="flex items-center justify-end">
                <Link
                  href="/forgot-password"
                  className="text-sm text-purple-400 hover:text-purple-300 transition"
                >
                  Forgot password?
                </Link>
              </div>

              <Button
                type="submit"
                className="w-full h-12 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white font-medium text-base shadow-lg shadow-purple-500/25"
                disabled={loading || !!oauthLoading}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  'Sign In'
                )}
              </Button>
            </form>

            {/* Sign Up Link */}
            <p className="text-center text-slate-400 mt-8">
              Don&apos;t have an account?{' '}
              <Link href="/sign-up" className="text-purple-400 hover:text-purple-300 font-medium transition">
                Create account
              </Link>
            </p>
          </div>

          {/* Footer */}
          <p className="text-center text-xs text-slate-600 mt-8">
            By signing in, you agree to our{' '}
            <Link href="/terms" className="text-slate-500 hover:text-slate-400">Terms of Service</Link>
            {' '}and{' '}
            <Link href="/privacy" className="text-slate-500 hover:text-slate-400">Privacy Policy</Link>
          </p>
        </div>
      </div>
    </div>
  )
}

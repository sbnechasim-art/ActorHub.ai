'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Shield, ArrowLeft, Check } from 'lucide-react'

export default function SignUpPage() {
  const router = useRouter()
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match')
      setLoading(false)
      return
    }

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/users/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          first_name: formData.firstName,
          last_name: formData.lastName,
        }),
      })

      if (response.ok) {
        router.push('/sign-in?registered=true')
      } else {
        const errorData = await response.json()
        // Handle FastAPI validation errors (detail can be array of objects)
        let errorMessage = 'Registration failed'
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail
        } else if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
          // Extract message from first validation error
          errorMessage = errorData.detail[0].msg || 'Validation error'
        }
        setError(errorMessage)
      }
    } catch (err) {
      setError('Connection error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const benefits = [
    'Protect your digital identity globally',
    'Monetize your likeness with AI licensing',
    'Real-time deepfake detection alerts',
    'Access to Actor Pack marketplace',
  ]

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-900 to-black flex items-center justify-center p-4">
      <div className="w-full max-w-4xl grid md:grid-cols-2 gap-8">
        {/* Left side - Benefits */}
        <div className="hidden md:flex flex-col justify-center">
          <h1 className="text-3xl font-bold text-white mb-6">
            Join ActorHub.ai
          </h1>
          <p className="text-gray-400 mb-8">
            The global platform for digital identity protection and monetization.
          </p>
          <ul className="space-y-4">
            {benefits.map((benefit, index) => (
              <li key={index} className="flex items-center text-gray-300">
                <div className="p-1 bg-green-500/20 rounded-full mr-3">
                  <Check className="w-4 h-4 text-green-400" />
                </div>
                {benefit}
              </li>
            ))}
          </ul>
        </div>

        {/* Right side - Form */}
        <div>
          <Link href="/" className="inline-flex items-center text-gray-400 hover:text-white mb-8">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to home
          </Link>

          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader className="text-center">
              <div className="flex justify-center mb-4">
                <div className="p-3 bg-purple-600/20 rounded-full">
                  <Shield className="w-8 h-8 text-purple-400" />
                </div>
              </div>
              <CardTitle className="text-2xl text-white">Create account</CardTitle>
              <CardDescription className="text-gray-400">
                Start protecting your digital identity today
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSignUp} className="space-y-4">
                {error && (
                  <div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
                    {error}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm text-gray-300">First name</label>
                    <Input
                      type="text"
                      placeholder="John"
                      value={formData.firstName}
                      onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                      className="bg-gray-900/50 border-gray-700 text-white"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-gray-300">Last name</label>
                    <Input
                      type="text"
                      placeholder="Doe"
                      value={formData.lastName}
                      onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                      className="bg-gray-900/50 border-gray-700 text-white"
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm text-gray-300">Email</label>
                  <Input
                    type="email"
                    placeholder="you@example.com"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="bg-gray-900/50 border-gray-700 text-white"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm text-gray-300">Password</label>
                  <Input
                    type="password"
                    placeholder="••••••••"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="bg-gray-900/50 border-gray-700 text-white"
                    required
                    minLength={8}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm text-gray-300">Confirm password</label>
                  <Input
                    type="password"
                    placeholder="••••••••"
                    value={formData.confirmPassword}
                    onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                    className="bg-gray-900/50 border-gray-700 text-white"
                    required
                  />
                </div>

                <Button
                  type="submit"
                  className="w-full bg-purple-600 hover:bg-purple-700"
                  disabled={loading}
                >
                  {loading ? 'Creating account...' : 'Create Account'}
                </Button>

                <div className="text-center text-sm text-gray-400">
                  Already have an account?{' '}
                  <Link href="/sign-in" className="text-purple-400 hover:text-purple-300">
                    Sign in
                  </Link>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

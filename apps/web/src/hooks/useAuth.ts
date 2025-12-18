'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { logger } from '@/lib/logger'

interface User {
  id: string
  email: string
  first_name: string | null
  last_name: string | null
  display_name: string | null
  role: string
  tier: string
  is_verified: boolean
}

interface AuthState {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export function useAuth() {
  const router = useRouter()
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  })

  // Check if user is authenticated on mount
  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = useCallback(async () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null

    if (!token) {
      setState({ user: null, isLoading: false, isAuthenticated: false })
      return
    }

    try {
      const response = await fetch(`${API_URL}/users/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (response.ok) {
        const user = await response.json()
        setState({ user, isLoading: false, isAuthenticated: true })
      } else {
        // Token is invalid, clear it
        localStorage.removeItem('token')
        setState({ user: null, isLoading: false, isAuthenticated: false })
      }
    } catch (error) {
      logger.error('Auth check failed', error)
      setState({ user: null, isLoading: false, isAuthenticated: false })
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    try {
      const response = await fetch(`${API_URL}/users/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      if (response.ok) {
        const data = await response.json()
        localStorage.setItem('token', data.access_token)
        setState({ user: data.user, isLoading: false, isAuthenticated: true })
        return { success: true }
      } else {
        const errorData = await response.json()
        // Handle FastAPI validation errors (detail can be array of objects)
        let errorMessage = 'Login failed'
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail
        } else if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
          errorMessage = errorData.detail[0].msg || 'Validation error'
        }
        return { success: false, error: errorMessage }
      }
    } catch (error) {
      return { success: false, error: 'Connection error. Please try again.' }
    }
  }, [])

  const register = useCallback(async (data: {
    email: string
    password: string
    first_name?: string
    last_name?: string
  }) => {
    try {
      const response = await fetch(`${API_URL}/users/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })

      if (response.ok) {
        return { success: true }
      } else {
        const errorData = await response.json()
        // Handle FastAPI validation errors (detail can be array of objects)
        let errorMessage = 'Registration failed'
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail
        } else if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
          errorMessage = errorData.detail[0].msg || 'Validation error'
        }
        return { success: false, error: errorMessage }
      }
    } catch (error) {
      return { success: false, error: 'Connection error. Please try again.' }
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setState({ user: null, isLoading: false, isAuthenticated: false })
    router.push('/')
  }, [router])

  const requireAuth = useCallback(() => {
    if (!state.isLoading && !state.isAuthenticated) {
      router.push('/sign-in')
    }
  }, [state.isLoading, state.isAuthenticated, router])

  return {
    user: state.user,
    isLoading: state.isLoading,
    isAuthenticated: state.isAuthenticated,
    login,
    register,
    logout,
    checkAuth,
    requireAuth,
  }
}

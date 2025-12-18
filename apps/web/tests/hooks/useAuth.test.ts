import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../mocks/server'

// Mock next/navigation
const mockPush = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    back: vi.fn(),
  }),
}))

const API_URL = 'http://localhost:8000/api/v1'

// Helper to configure localStorage mock
const setupLocalStorageMock = (initialToken: string | null = null) => {
  let store: Record<string, string> = {}
  if (initialToken) {
    store['token'] = initialToken
  }

  const mockGetItem = vi.fn((key: string) => store[key] ?? null)
  const mockSetItem = vi.fn((key: string, value: string) => { store[key] = value })
  const mockRemoveItem = vi.fn((key: string) => { delete store[key] })
  const mockClear = vi.fn(() => { store = {} })

  Object.defineProperty(window, 'localStorage', {
    value: {
      getItem: mockGetItem,
      setItem: mockSetItem,
      removeItem: mockRemoveItem,
      clear: mockClear,
    },
    writable: true,
  })

  return { mockGetItem, mockSetItem, mockRemoveItem, mockClear }
}

describe('useAuth Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockPush.mockClear()
    vi.resetModules()
  })

  afterEach(() => {
    server.resetHandlers()
  })

  describe('Initial State', () => {
    it('should set unauthenticated when no token exists', async () => {
      setupLocalStorageMock(null)

      const { useAuth } = await import('@/hooks/useAuth')
      const { result } = renderHook(() => useAuth())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.isAuthenticated).toBe(false)
      expect(result.current.user).toBe(null)
    })

    it('should check for existing token and validate', async () => {
      setupLocalStorageMock('valid_token')

      // Override MSW handler for this specific test
      server.use(
        http.get(`${API_URL}/users/me`, () => {
          return HttpResponse.json({
            id: '123',
            email: 'test@example.com',
            first_name: 'Test',
            last_name: 'User',
            display_name: 'TestUser',
            role: 'creator',
            tier: 'free',
            is_verified: true,
          })
        })
      )

      const { useAuth } = await import('@/hooks/useAuth')
      const { result } = renderHook(() => useAuth())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true)
      })

      expect(result.current.user?.email).toBe('test@example.com')
    })

    it('should handle invalid token gracefully', async () => {
      const { mockRemoveItem } = setupLocalStorageMock('invalid_token')

      // Override MSW handler to return 401
      server.use(
        http.get(`${API_URL}/users/me`, () => {
          return new HttpResponse(null, { status: 401 })
        })
      )

      const { useAuth } = await import('@/hooks/useAuth')
      const { result } = renderHook(() => useAuth())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.isAuthenticated).toBe(false)
      expect(mockRemoveItem).toHaveBeenCalledWith('token')
    })
  })

  describe('Login', () => {
    it('should login successfully with valid credentials', async () => {
      const { mockSetItem } = setupLocalStorageMock(null)

      // Override MSW handler for login
      server.use(
        http.get(`${API_URL}/users/me`, () => {
          return new HttpResponse(null, { status: 401 })
        }),
        http.post(`${API_URL}/users/login`, () => {
          return HttpResponse.json({
            access_token: 'new_token',
            user: {
              id: '123',
              email: 'test@example.com',
              first_name: 'Test',
              last_name: 'User',
              display_name: 'TestUser',
              role: 'creator',
              tier: 'free',
              is_verified: true,
            },
          })
        })
      )

      const { useAuth } = await import('@/hooks/useAuth')
      const { result } = renderHook(() => useAuth())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      let loginResult: { success: boolean; error?: string }
      await act(async () => {
        loginResult = await result.current.login('test@example.com', 'password123')
      })

      expect(loginResult!.success).toBe(true)
      expect(mockSetItem).toHaveBeenCalledWith('token', 'new_token')
    })

    it('should return error for invalid credentials', async () => {
      setupLocalStorageMock(null)

      server.use(
        http.get(`${API_URL}/users/me`, () => {
          return new HttpResponse(null, { status: 401 })
        }),
        http.post(`${API_URL}/users/login`, () => {
          return HttpResponse.json(
            { detail: 'Invalid email or password' },
            { status: 401 }
          )
        })
      )

      const { useAuth } = await import('@/hooks/useAuth')
      const { result } = renderHook(() => useAuth())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      let loginResult: { success: boolean; error?: string }
      await act(async () => {
        loginResult = await result.current.login('wrong@email.com', 'wrongpassword')
      })

      expect(loginResult!.success).toBe(false)
      expect(loginResult!.error).toBe('Invalid email or password')
    })

    it('should handle network errors', async () => {
      setupLocalStorageMock(null)

      server.use(
        http.get(`${API_URL}/users/me`, () => {
          return new HttpResponse(null, { status: 401 })
        }),
        http.post(`${API_URL}/users/login`, () => {
          return HttpResponse.error()
        })
      )

      const { useAuth } = await import('@/hooks/useAuth')
      const { result } = renderHook(() => useAuth())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      let loginResult: { success: boolean; error?: string }
      await act(async () => {
        loginResult = await result.current.login('test@example.com', 'password123')
      })

      expect(loginResult!.success).toBe(false)
      expect(loginResult!.error).toContain('Connection error')
    })
  })

  describe('Register', () => {
    it('should register successfully', async () => {
      setupLocalStorageMock(null)

      server.use(
        http.get(`${API_URL}/users/me`, () => {
          return new HttpResponse(null, { status: 401 })
        }),
        http.post(`${API_URL}/users/register`, () => {
          return HttpResponse.json({
            id: 'new-user-id',
            email: 'new@example.com',
            first_name: 'New',
          })
        })
      )

      const { useAuth } = await import('@/hooks/useAuth')
      const { result } = renderHook(() => useAuth())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      let registerResult: { success: boolean; error?: string }
      await act(async () => {
        registerResult = await result.current.register({
          email: 'new@example.com',
          password: 'password123',
          first_name: 'New',
        })
      })

      expect(registerResult!.success).toBe(true)
    })

    it('should return error for existing email', async () => {
      setupLocalStorageMock(null)

      server.use(
        http.get(`${API_URL}/users/me`, () => {
          return new HttpResponse(null, { status: 401 })
        }),
        http.post(`${API_URL}/users/register`, () => {
          return HttpResponse.json(
            { detail: 'Email already registered' },
            { status: 400 }
          )
        })
      )

      const { useAuth } = await import('@/hooks/useAuth')
      const { result } = renderHook(() => useAuth())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      let registerResult: { success: boolean; error?: string }
      await act(async () => {
        registerResult = await result.current.register({
          email: 'existing@example.com',
          password: 'password123',
        })
      })

      expect(registerResult!.success).toBe(false)
      expect(registerResult!.error).toBe('Email already registered')
    })
  })

  describe('Logout', () => {
    it('should logout and clear state', async () => {
      const { mockRemoveItem } = setupLocalStorageMock('existing_token')

      server.use(
        http.get(`${API_URL}/users/me`, () => {
          return HttpResponse.json({
            id: '123',
            email: 'test@example.com',
            first_name: 'Test',
            last_name: null,
            display_name: 'TestUser',
            role: 'creator',
            tier: 'free',
            is_verified: true,
          })
        })
      )

      const { useAuth } = await import('@/hooks/useAuth')
      const { result } = renderHook(() => useAuth())

      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true)
      })

      act(() => {
        result.current.logout()
      })

      expect(result.current.isAuthenticated).toBe(false)
      expect(result.current.user).toBe(null)
      expect(mockRemoveItem).toHaveBeenCalledWith('token')
      expect(mockPush).toHaveBeenCalledWith('/')
    })
  })

  describe('requireAuth', () => {
    it('should redirect to login when not authenticated', async () => {
      setupLocalStorageMock(null)

      const { useAuth } = await import('@/hooks/useAuth')
      const { result } = renderHook(() => useAuth())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      act(() => {
        result.current.requireAuth()
      })

      expect(mockPush).toHaveBeenCalledWith('/sign-in')
    })

    it('should not redirect when authenticated', async () => {
      setupLocalStorageMock('existing_token')

      server.use(
        http.get(`${API_URL}/users/me`, () => {
          return HttpResponse.json({
            id: '123',
            email: 'test@example.com',
            first_name: 'Test',
            last_name: null,
            display_name: null,
            role: 'creator',
            tier: 'free',
            is_verified: true,
          })
        })
      )

      const { useAuth } = await import('@/hooks/useAuth')
      const { result } = renderHook(() => useAuth())

      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true)
      })

      mockPush.mockClear()

      act(() => {
        result.current.requireAuth()
      })

      expect(mockPush).not.toHaveBeenCalled()
    })
  })

  describe('Token Expiry', () => {
    it('should handle expired token', async () => {
      const { mockRemoveItem } = setupLocalStorageMock('expired_token')

      server.use(
        http.get(`${API_URL}/users/me`, () => {
          return new HttpResponse(null, { status: 401 })
        })
      )

      const { useAuth } = await import('@/hooks/useAuth')
      const { result } = renderHook(() => useAuth())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.isAuthenticated).toBe(false)
      expect(mockRemoveItem).toHaveBeenCalledWith('token')
    })
  })
})

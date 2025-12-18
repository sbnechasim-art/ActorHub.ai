import React, { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Create a new QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

// All providers wrapper
interface AllProvidersProps {
  children: React.ReactNode
}

function AllProviders({ children }: AllProvidersProps) {
  const queryClient = createTestQueryClient()

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

// Custom render function with providers
const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllProviders, ...options })

// Re-export everything from testing-library
export * from '@testing-library/react'
export { customRender as render }

// Helper to create a wrapper with specific QueryClient
export function createWrapper() {
  const queryClient = createTestQueryClient()
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

// Helper to wait for loading states to resolve
export async function waitForLoadingToFinish() {
  const { waitFor } = await import('@testing-library/react')
  await waitFor(() => {
    const loadingElements = document.querySelectorAll('[aria-busy="true"]')
    expect(loadingElements.length).toBe(0)
  })
}

// Helper for form testing
export async function fillForm(
  user: ReturnType<typeof import('@testing-library/user-event').default.setup>,
  fields: Record<string, string>
) {
  for (const [name, value] of Object.entries(fields)) {
    const input = document.querySelector(`[name="${name}"]`) as HTMLInputElement
    if (input) {
      await user.clear(input)
      await user.type(input, value)
    }
  }
}

// Mock authenticated user context
export const mockAuthenticatedUser = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  email: 'test@actorhub.ai',
  first_name: 'Test',
  last_name: 'User',
  display_name: 'TestUser',
  role: 'creator',
  tier: 'pro',
  is_verified: true,
}

// Setup localStorage with auth token
export function setupAuthenticatedState() {
  localStorage.setItem('token', 'mock_access_token_12345')
}

// Clear auth state
export function clearAuthState() {
  localStorage.removeItem('token')
}

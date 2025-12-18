import { http, HttpResponse } from 'msw'

const API_URL = 'http://localhost:8000/api/v1'

// Mock data
export const mockUser = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  email: 'test@actorhub.ai',
  first_name: 'Test',
  last_name: 'User',
  display_name: 'TestUser',
  role: 'creator',
  tier: 'pro',
  is_verified: true,
}

export const mockIdentities = [
  {
    id: '123e4567-e89b-12d3-a456-426614174001',
    user_id: mockUser.id,
    name: 'Test Actor',
    display_name: 'Test Actor',
    bio: 'A professional test actor for AI projects',
    category: 'actor',
    status: 'VERIFIED',
    protection_level: 'PREMIUM',
    is_public: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
    verified_at: '2024-01-02T00:00:00Z',
    total_verifications: 523,
    total_revenue: 1250.00,
    profile_image_url: '/mock-avatar.jpg',
    actor_pack: {
      id: 'pack-001',
      identity_id: '123e4567-e89b-12d3-a456-426614174001',
      training_status: 'COMPLETED',
      training_progress: 100,
      quality_score: 92,
      authenticity_score: 95,
      consistency_score: 89,
      is_available: true,
    },
  },
  {
    id: '123e4567-e89b-12d3-a456-426614174002',
    user_id: mockUser.id,
    name: 'Another Actor',
    display_name: 'Another Actor',
    bio: 'Another test actor for testing',
    category: 'model',
    status: 'PENDING',
    protection_level: 'STANDARD',
    is_public: false,
    created_at: '2024-01-10T00:00:00Z',
    updated_at: '2024-01-10T00:00:00Z',
    total_verifications: 0,
    total_revenue: 0,
    actor_pack: {
      id: 'pack-002',
      identity_id: '123e4567-e89b-12d3-a456-426614174002',
      training_status: 'PROCESSING',
      training_progress: 65,
      quality_score: null,
      is_available: false,
    },
  },
]

export const mockLicenses = [
  {
    id: '123e4567-e89b-12d3-a456-426614174010',
    identity_id: '123e4567-e89b-12d3-a456-426614174001',
    licensee_id: 'licensee-001',
    license_type: 'COMMERCIAL',
    price: 99.00,
    currency: 'USD',
    is_active: true,
    payment_status: 'PAID',
    expires_at: '2025-01-01T00:00:00Z',
    created_at: '2024-01-15T00:00:00Z',
    identity: mockIdentities[0],
  },
  {
    id: '123e4567-e89b-12d3-a456-426614174011',
    identity_id: '123e4567-e89b-12d3-a456-426614174001',
    licensee_id: 'licensee-002',
    license_type: 'PERSONAL',
    price: 29.00,
    currency: 'USD',
    is_active: true,
    payment_status: 'PAID',
    expires_at: '2024-12-01T00:00:00Z',
    created_at: '2024-01-10T00:00:00Z',
    identity: mockIdentities[0],
  },
]

export const mockNotifications = [
  {
    id: '123e4567-e89b-12d3-a456-426614174020',
    type: 'BILLING',
    title: 'New License Purchase',
    message: 'Someone purchased a commercial license for your identity "Test Actor"',
    action_url: '/licenses/123e4567-e89b-12d3-a456-426614174010',
    is_read: false,
    created_at: '2024-01-15T10:00:00Z',
  },
  {
    id: '123e4567-e89b-12d3-a456-426614174021',
    type: 'TRAINING',
    title: 'Training Complete',
    message: 'Your identity "Test Actor" training has completed successfully',
    action_url: '/identity/123e4567-e89b-12d3-a456-426614174001',
    is_read: true,
    created_at: '2024-01-14T10:00:00Z',
  },
  {
    id: '123e4567-e89b-12d3-a456-426614174022',
    type: 'DETECTION',
    title: 'Unauthorized Use Detected',
    message: 'We detected potential unauthorized use of your identity',
    action_url: '/dashboard/analytics',
    is_read: false,
    created_at: '2024-01-13T10:00:00Z',
  },
]

export const mockDashboardStats = {
  identities_count: 2,
  total_revenue: 1250.00,
  verification_checks: 523,
  active_licenses: 5,
}

export const mockAnalyticsDashboard = {
  usage: {
    total_verifications: 523,
    total_generations: 150,
    total_api_calls: 1200,
    period_start: '2024-01-01',
    period_end: '2024-01-31',
  },
  revenue: {
    total_revenue: 1250.00,
    total_payouts: 1000.00,
    net_earnings: 1000.00,
    transaction_count: 15,
    currency: 'USD',
  },
  top_identities: [
    {
      identity_id: '123e4567-e89b-12d3-a456-426614174001',
      identity_name: 'Test Actor',
      verifications: 400,
      licenses_sold: 10,
      revenue: 990.00,
    },
    {
      identity_id: '123e4567-e89b-12d3-a456-426614174002',
      identity_name: 'Another Actor',
      verifications: 123,
      licenses_sold: 5,
      revenue: 260.00,
    },
  ],
  usage_trend: [
    { date: '2024-01-01', value: 50 },
    { date: '2024-01-08', value: 75 },
    { date: '2024-01-15', value: 100 },
    { date: '2024-01-22', value: 150 },
    { date: '2024-01-29', value: 148 },
  ],
  revenue_trend: [
    { date: '2024-01-01', value: 100 },
    { date: '2024-01-08', value: 200 },
    { date: '2024-01-15', value: 350 },
    { date: '2024-01-22', value: 400 },
    { date: '2024-01-29', value: 200 },
  ],
}

export const mockPayoutSettings = {
  method: 'paypal',
  paypal_email: 'test@paypal.com',
  available_balance: 450.00,
  pending_balance: 100.00,
  minimum_payout: 50.00,
  currency: 'USD',
}

export const mockPayoutHistory = [
  {
    id: 'payout-001',
    amount: 500.00,
    currency: 'USD',
    status: 'COMPLETED',
    method: 'PayPal',
    created_at: '2024-01-01T00:00:00Z',
    completed_at: '2024-01-02T00:00:00Z',
  },
  {
    id: 'payout-002',
    amount: 300.00,
    currency: 'USD',
    status: 'PENDING',
    method: 'PayPal',
    created_at: '2024-01-15T00:00:00Z',
  },
]

export const mockSubscription = {
  id: 'sub-001',
  plan: 'pro',
  status: 'active',
  current_period_start: '2024-01-01T00:00:00Z',
  current_period_end: '2024-02-01T00:00:00Z',
  cancel_at_period_end: false,
}

export const mockPlans = [
  {
    id: 'free',
    name: 'Free',
    price_monthly: 0,
    price_yearly: 0,
    features: ['1 identity', 'Basic analytics', 'Community support'],
    limits: { identities: 1, api_calls: 100 },
  },
  {
    id: 'pro',
    name: 'Pro',
    price_monthly: 29,
    price_yearly: 290,
    features: ['10 identities', 'Advanced analytics', 'API access', 'Priority support'],
    limits: { identities: 10, api_calls: 10000 },
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price_monthly: 199,
    price_yearly: 1990,
    features: ['Unlimited identities', 'Full analytics suite', 'Custom integrations', 'Dedicated support'],
    limits: { identities: -1, api_calls: -1 },
  },
]

export const mockMarketplaceListings = mockIdentities.filter((i) => i.is_public).map((identity) => ({
  ...identity,
  pricing: {
    personal: 29.00,
    commercial: 99.00,
    enterprise: 499.00,
  },
  stats: {
    downloads: 150,
    rating: 4.8,
    reviews: 25,
  },
}))

export const handlers = [
  // Auth endpoints
  http.post(`${API_URL}/users/login`, async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string }
    if (body.email === 'test@actorhub.ai' && body.password === 'password123') {
      return HttpResponse.json({
        access_token: 'mock_access_token_12345',
        refresh_token: 'mock_refresh_token_12345',
        user: mockUser,
      })
    }
    return HttpResponse.json({ detail: 'Invalid email or password' }, { status: 401 })
  }),

  http.post(`${API_URL}/users/register`, async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string; first_name?: string }
    if (body.email === 'existing@actorhub.ai') {
      return HttpResponse.json({ detail: 'Email already registered' }, { status: 400 })
    }
    return HttpResponse.json(
      {
        id: 'new-user-id',
        email: body.email,
        first_name: body.first_name || null,
        message: 'Registration successful. Please verify your email.',
      },
      { status: 201 }
    )
  }),

  http.post(`${API_URL}/auth/refresh`, () => {
    return HttpResponse.json({ access_token: 'new_mock_access_token' })
  }),

  // User endpoints
  http.get(`${API_URL}/users/me`, () => {
    return HttpResponse.json(mockUser)
  }),

  http.patch(`${API_URL}/users/me`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ ...mockUser, ...body })
  }),

  http.get(`${API_URL}/users/me/dashboard`, () => {
    return HttpResponse.json(mockDashboardStats)
  }),

  http.get(`${API_URL}/users/api-keys`, () => {
    return HttpResponse.json([
      { id: 'key-1', name: 'Production', prefix: 'ak_prod_***', created_at: '2024-01-01T00:00:00Z' },
      { id: 'key-2', name: 'Development', prefix: 'ak_dev_***', created_at: '2024-01-10T00:00:00Z' },
    ])
  }),

  http.post(`${API_URL}/users/api-keys`, async ({ request }) => {
    const body = (await request.json()) as { name: string }
    return HttpResponse.json({
      id: 'new-key-id',
      name: body.name,
      key: 'ak_new_key_full_value_shown_once',
      prefix: 'ak_new_***',
      created_at: new Date().toISOString(),
    })
  }),

  http.delete(`${API_URL}/users/api-keys/:id`, () => {
    return HttpResponse.json({ success: true })
  }),

  // Identity endpoints
  http.get(`${API_URL}/identity/mine`, () => {
    return HttpResponse.json(mockIdentities)
  }),

  http.get(`${API_URL}/identity/:id`, ({ params }) => {
    const identity = mockIdentities.find((i) => i.id === params.id)
    if (identity) {
      return HttpResponse.json(identity)
    }
    return HttpResponse.json({ detail: 'Identity not found' }, { status: 404 })
  }),

  http.post(`${API_URL}/identity/register`, async ({ request }) => {
    const formData = await request.formData()
    const name = formData.get('name') as string
    return HttpResponse.json(
      {
        id: '123e4567-e89b-12d3-a456-426614174099',
        user_id: mockUser.id,
        name: name,
        display_name: name,
        status: 'PENDING',
        protection_level: 'BASIC',
        is_public: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        actor_pack: {
          id: 'pack-new',
          training_status: 'PENDING',
          training_progress: 0,
        },
      },
      { status: 201 }
    )
  }),

  http.patch(`${API_URL}/identity/:id`, async ({ params, request }) => {
    const body = await request.json()
    const identity = mockIdentities.find((i) => i.id === params.id)
    if (identity) {
      return HttpResponse.json({ ...identity, ...body, updated_at: new Date().toISOString() })
    }
    return HttpResponse.json({ detail: 'Identity not found' }, { status: 404 })
  }),

  http.delete(`${API_URL}/identity/:id`, ({ params }) => {
    const identity = mockIdentities.find((i) => i.id === params.id)
    if (identity) {
      return HttpResponse.json({ success: true, message: 'Identity deleted successfully' })
    }
    return HttpResponse.json({ detail: 'Identity not found' }, { status: 404 })
  }),

  http.post(`${API_URL}/identity/verify`, async () => {
    return HttpResponse.json({
      is_match: true,
      confidence: 0.95,
      identity_id: mockIdentities[0].id,
      identity_name: mockIdentities[0].display_name,
    })
  }),

  // Licenses endpoints
  http.get(`${API_URL}/marketplace/licenses/mine`, ({ request }) => {
    const url = new URL(request.url)
    const status = url.searchParams.get('status')
    let filteredLicenses = mockLicenses
    if (status === 'active') {
      filteredLicenses = mockLicenses.filter((l) => l.is_active)
    } else if (status === 'expired') {
      filteredLicenses = mockLicenses.filter((l) => !l.is_active)
    }
    return HttpResponse.json({ licenses: filteredLicenses, total: filteredLicenses.length })
  }),

  http.get(`${API_URL}/marketplace/licenses/:id`, ({ params }) => {
    const license = mockLicenses.find((l) => l.id === params.id)
    if (license) {
      return HttpResponse.json(license)
    }
    return HttpResponse.json({ detail: 'License not found' }, { status: 404 })
  }),

  // Notifications endpoints
  http.get(`${API_URL}/notifications`, ({ request }) => {
    const url = new URL(request.url)
    const isRead = url.searchParams.get('is_read')
    let filteredNotifications = mockNotifications
    if (isRead === 'false') {
      filteredNotifications = mockNotifications.filter((n) => !n.is_read)
    } else if (isRead === 'true') {
      filteredNotifications = mockNotifications.filter((n) => n.is_read)
    }
    return HttpResponse.json({
      notifications: filteredNotifications,
      total: filteredNotifications.length,
      unread_count: mockNotifications.filter((n) => !n.is_read).length,
    })
  }),

  http.get(`${API_URL}/notifications/unread-count`, () => {
    return HttpResponse.json({ unread_count: mockNotifications.filter((n) => !n.is_read).length })
  }),

  http.post(`${API_URL}/notifications/:id/read`, ({ params }) => {
    const notification = mockNotifications.find((n) => n.id === params.id)
    if (notification) {
      return HttpResponse.json({ success: true })
    }
    return HttpResponse.json({ detail: 'Notification not found' }, { status: 404 })
  }),

  http.post(`${API_URL}/notifications/read-all`, () => {
    return HttpResponse.json({ success: true, count: mockNotifications.filter((n) => !n.is_read).length })
  }),

  http.delete(`${API_URL}/notifications/:id`, () => {
    return HttpResponse.json({ success: true })
  }),

  http.get(`${API_URL}/notifications/preferences`, () => {
    return HttpResponse.json({
      email_marketing: true,
      email_billing: true,
      email_security: true,
      push_all: false,
    })
  }),

  http.put(`${API_URL}/notifications/preferences`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json(body)
  }),

  // Analytics endpoints
  http.get(`${API_URL}/analytics/dashboard`, () => {
    return HttpResponse.json(mockAnalyticsDashboard)
  }),

  http.get(`${API_URL}/analytics/usage`, () => {
    return HttpResponse.json(mockAnalyticsDashboard.usage_trend)
  }),

  http.get(`${API_URL}/analytics/revenue`, () => {
    return HttpResponse.json(mockAnalyticsDashboard.revenue_trend)
  }),

  http.get(`${API_URL}/analytics/identity/:id`, () => {
    return HttpResponse.json({
      identity: mockIdentities[0],
      stats: mockAnalyticsDashboard.top_identities[0],
      usage_trend: mockAnalyticsDashboard.usage_trend,
      revenue_trend: mockAnalyticsDashboard.revenue_trend,
    })
  }),

  // Marketplace endpoints
  http.get(`${API_URL}/marketplace/listings`, () => {
    return HttpResponse.json(mockMarketplaceListings)
  }),

  http.get(`${API_URL}/marketplace/listings/:id`, ({ params }) => {
    const listing = mockMarketplaceListings.find((l) => l.id === params.id)
    if (listing) {
      return HttpResponse.json(listing)
    }
    return HttpResponse.json({ detail: 'Listing not found' }, { status: 404 })
  }),

  http.post(`${API_URL}/marketplace/license/price`, async ({ request }) => {
    const body = (await request.json()) as { identity_id: string; license_type: string }
    const prices: Record<string, number> = { PERSONAL: 29, COMMERCIAL: 99, ENTERPRISE: 499 }
    return HttpResponse.json({
      price: prices[body.license_type] || 99,
      currency: 'USD',
    })
  }),

  http.post(`${API_URL}/marketplace/license/purchase`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({
      checkout_url: 'https://checkout.stripe.com/mock-session',
      session_id: 'mock_session_id',
    })
  }),

  // Subscription endpoints
  http.get(`${API_URL}/subscriptions/current`, () => {
    return HttpResponse.json(mockSubscription)
  }),

  http.get(`${API_URL}/subscriptions/plans`, () => {
    return HttpResponse.json(mockPlans)
  }),

  http.get(`${API_URL}/subscriptions/usage`, () => {
    return HttpResponse.json({
      identities_used: 2,
      identities_limit: 10,
      api_calls_used: 1200,
      api_calls_limit: 10000,
      period_start: '2024-01-01',
      period_end: '2024-02-01',
    })
  }),

  http.post(`${API_URL}/subscriptions/checkout`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({
      checkout_url: 'https://checkout.stripe.com/mock-subscription-session',
      session_id: 'mock_sub_session_id',
    })
  }),

  http.post(`${API_URL}/subscriptions/cancel`, () => {
    return HttpResponse.json({ success: true, cancel_at_period_end: true })
  }),

  http.post(`${API_URL}/subscriptions/reactivate`, () => {
    return HttpResponse.json({ success: true, cancel_at_period_end: false })
  }),

  // Payout endpoints
  http.get(`${API_URL}/users/payout-settings`, () => {
    return HttpResponse.json(mockPayoutSettings)
  }),

  http.put(`${API_URL}/users/payout-settings`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ ...mockPayoutSettings, ...body })
  }),

  http.get(`${API_URL}/admin/payouts/history`, () => {
    return HttpResponse.json({ payouts: mockPayoutHistory, total: mockPayoutHistory.length })
  }),

  http.post(`${API_URL}/users/request-payout`, () => {
    if (mockPayoutSettings.available_balance < mockPayoutSettings.minimum_payout) {
      return HttpResponse.json(
        { detail: `Minimum payout amount is $${mockPayoutSettings.minimum_payout}` },
        { status: 400 }
      )
    }
    return HttpResponse.json({
      id: 'new-payout-id',
      amount: mockPayoutSettings.available_balance,
      status: 'PENDING',
      created_at: new Date().toISOString(),
    })
  }),

  // Actor Pack endpoints
  http.get(`${API_URL}/actor-pack/public`, () => {
    return HttpResponse.json(mockMarketplaceListings)
  }),

  http.get(`${API_URL}/actor-pack/status/:id`, ({ params }) => {
    const identity = mockIdentities.find((i) => i.actor_pack?.id === params.id || i.id === params.id)
    if (identity?.actor_pack) {
      return HttpResponse.json(identity.actor_pack)
    }
    return HttpResponse.json({ detail: 'Actor pack not found' }, { status: 404 })
  }),

  http.post(`${API_URL}/actor-pack/train`, async () => {
    return HttpResponse.json({
      id: 'new-pack-id',
      training_status: 'PROCESSING',
      training_progress: 0,
      message: 'Training initiated successfully',
    })
  }),

  http.get(`${API_URL}/actor-pack/download/:id`, () => {
    return HttpResponse.json({
      download_url: 'https://storage.example.com/mock-download-url',
      expires_at: new Date(Date.now() + 3600000).toISOString(),
    })
  }),

  // Health check
  http.get(`${API_URL}/health`, () => {
    return HttpResponse.json({ status: 'healthy', version: '1.0.0', timestamp: new Date().toISOString() })
  }),
]

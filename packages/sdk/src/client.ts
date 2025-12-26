/**
 * ActorHub API Client
 */
import axios, { AxiosInstance, AxiosError } from 'axios'
import type {
  ActorHubConfig,
  Identity,
  VerifyRequest,
  VerifyResponse,
  RegisterRequest,
  RegisterResponse,
  ActorPack,
  Listing,
  License,
  PurchaseLicenseRequest,
  UsageLog,
  DashboardStats,
  SDKError,
} from './types'

const DEFAULT_BASE_URL = 'https://api.actorhub.ai/v1'
const DEFAULT_TIMEOUT = 30000

export class ActorHubClient {
  private client: AxiosInstance
  private apiKey: string

  constructor(config: ActorHubConfig) {
    this.apiKey = config.apiKey

    this.client = axios.create({
      baseURL: config.baseUrl || DEFAULT_BASE_URL,
      timeout: config.timeout || DEFAULT_TIMEOUT,
      headers: {
        'X-API-Key': config.apiKey,
        'Content-Type': 'application/json',
        'User-Agent': 'ActorHub-SDK/1.0.0',
      },
    })

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        throw this.handleError(error)
      }
    )
  }

  private handleError(error: AxiosError): SDKError {
    const sdkError = new Error(
      (error.response?.data as any)?.detail || error.message
    ) as SDKError

    sdkError.code = (error.response?.data as any)?.code || 'UNKNOWN_ERROR'
    sdkError.status = error.response?.status
    sdkError.details = error.response?.data as Record<string, unknown>

    return sdkError
  }

  private toBase64(input: string | Buffer): string {
    if (typeof input === 'string') {
      if (input.startsWith('data:')) {
        return input.split(',')[1]
      }
      return input
    }
    return input.toString('base64')
  }

  // ============================================
  // Identity Verification (Core API)
  // ============================================

  /**
   * Verify if an image matches a registered identity.
   * This is the primary API for platforms to check content authorization.
   */
  async verify(request: VerifyRequest): Promise<VerifyResponse> {
    const response = await this.client.post<VerifyResponse>('/identity/verify', {
      image: this.toBase64(request.image),
      threshold: request.threshold,
      include_metadata: request.include_metadata,
    })
    return response.data
  }

  /**
   * Batch verify multiple images at once.
   */
  async verifyBatch(
    images: (string | Buffer)[],
    options?: { threshold?: number }
  ): Promise<VerifyResponse[]> {
    const response = await this.client.post<VerifyResponse[]>('/identity/verify/batch', {
      images: images.map((img) => this.toBase64(img)),
      threshold: options?.threshold,
    })
    return response.data
  }

  // ============================================
  // Identity Management
  // ============================================

  /**
   * Register a new identity with face images.
   */
  async registerIdentity(request: RegisterRequest): Promise<RegisterResponse> {
    const response = await this.client.post<RegisterResponse>('/identity/register', {
      face_image: this.toBase64(request.face_image),
      verification_image: this.toBase64(request.verification_image),
      display_name: request.display_name,
      protection_level: request.protection_level || 'free',
      allow_commercial: request.allow_commercial ?? false,
      allow_ai_training: request.allow_ai_training ?? false,
      blocked_categories: request.blocked_categories || [],
    })
    return response.data
  }

  /**
   * Get current user's identities.
   */
  async getMyIdentities(): Promise<Identity[]> {
    const response = await this.client.get<Identity[]>('/identity/mine')
    return response.data
  }

  /**
   * Get a specific identity by ID.
   */
  async getIdentity(identityId: string): Promise<Identity> {
    const response = await this.client.get<Identity>(`/identity/${identityId}`)
    return response.data
  }

  /**
   * Update identity settings.
   */
  async updateIdentity(
    identityId: string,
    updates: Partial<Pick<Identity, 'display_name' | 'protection_level' | 'allow_commercial' | 'allow_ai_training' | 'blocked_categories'>>
  ): Promise<Identity> {
    const response = await this.client.patch<Identity>(`/identity/${identityId}`, updates)
    return response.data
  }

  /**
   * Delete an identity.
   */
  async deleteIdentity(identityId: string): Promise<void> {
    await this.client.delete(`/identity/${identityId}`)
  }

  // ============================================
  // Actor Packs
  // ============================================

  /**
   * Get Actor Pack for an identity.
   */
  async getActorPack(identityId: string): Promise<ActorPack> {
    const response = await this.client.get<ActorPack>(`/actor-packs/${identityId}`)
    return response.data
  }

  /**
   * Start Actor Pack training.
   */
  async trainActorPack(
    identityId: string,
    options?: {
      include_voice?: boolean
      include_motion?: boolean
      audio_urls?: string[]
      video_urls?: string[]
    }
  ): Promise<ActorPack> {
    const response = await this.client.post<ActorPack>(`/actor-packs/${identityId}/train`, options)
    return response.data
  }

  /**
   * Get Actor Pack download URL.
   */
  async getActorPackDownload(actorPackId: string): Promise<{ url: string; expires_at: string }> {
    const response = await this.client.get<{ url: string; expires_at: string }>(
      `/actor-packs/${actorPackId}/download`
    )
    return response.data
  }

  // ============================================
  // Marketplace
  // ============================================

  /**
   * Browse marketplace listings.
   */
  async getListings(options?: {
    category?: string
    query?: string
    sort?: 'popular' | 'newest' | 'price_asc' | 'price_desc'
    page?: number
    limit?: number
  }): Promise<{ items: Listing[]; total: number; page: number }> {
    const response = await this.client.get('/marketplace/listings', { params: options })
    return response.data
  }

  /**
   * Get a specific listing.
   */
  async getListing(listingId: string): Promise<Listing> {
    const response = await this.client.get<Listing>(`/marketplace/listings/${listingId}`)
    return response.data
  }

  /**
   * Purchase a license.
   */
  async purchaseLicense(request: PurchaseLicenseRequest): Promise<License> {
    const response = await this.client.post<License>('/marketplace/purchase', request)
    return response.data
  }

  /**
   * Get user's active licenses.
   */
  async getMyLicenses(): Promise<License[]> {
    const response = await this.client.get<License[]>('/marketplace/licenses/mine')
    return response.data
  }

  // ============================================
  // Usage & Analytics
  // ============================================

  /**
   * Get usage logs for an identity.
   */
  async getUsageLogs(
    identityId: string,
    options?: { page?: number; limit?: number }
  ): Promise<{ items: UsageLog[]; total: number }> {
    const response = await this.client.get(`/identity/${identityId}/usage`, { params: options })
    return response.data
  }

  /**
   * Get dashboard statistics.
   */
  async getDashboardStats(): Promise<DashboardStats> {
    const response = await this.client.get<DashboardStats>('/users/me/dashboard')
    return response.data
  }

  /**
   * Get identity statistics.
   */
  async getIdentityStats(identityId: string): Promise<{
    total_verifications: number
    authorized_count: number
    unauthorized_count: number
    revenue: number
  }> {
    const response = await this.client.get(`/identity/${identityId}/stats`)
    return response.data
  }

  // ============================================
  // Content Generation (Actor Pack Usage)
  // ============================================

  /**
   * Generate face image using trained Actor Pack.
   */
  async generateFaceImage(
    actorPackId: string,
    options: {
      prompt: string
      negative_prompt?: string
      num_outputs?: number
      guidance_scale?: number
    }
  ): Promise<{ job_id: string; status: string }> {
    const response = await this.client.post(`/generation/face`, {
      actor_pack_id: actorPackId,
      ...options,
    })
    return response.data
  }

  /**
   * Generate voice using trained Actor Pack.
   */
  async generateVoice(
    actorPackId: string,
    options: {
      text: string
      model_id?: string
    }
  ): Promise<{ job_id: string; status: string }> {
    const response = await this.client.post(`/generation/voice`, {
      actor_pack_id: actorPackId,
      ...options,
    })
    return response.data
  }

  /**
   * Get generation job status.
   */
  async getGenerationJob(jobId: string): Promise<{
    id: string
    status: 'pending' | 'processing' | 'completed' | 'failed'
    type: 'face' | 'voice' | 'video'
    output_urls?: string[]
    error?: string
    created_at: string
    completed_at?: string
  }> {
    const response = await this.client.get(`/generation/jobs/${jobId}`)
    return response.data
  }

  // ============================================
  // Webhooks
  // ============================================

  /**
   * Register a webhook for events.
   */
  async registerWebhook(options: {
    url: string
    events: ('verification' | 'license.purchased' | 'training.completed' | 'unauthorized.detection')[]
    secret?: string
  }): Promise<{ id: string; url: string; events: string[]; secret: string }> {
    const response = await this.client.post('/webhooks', options)
    return response.data
  }

  /**
   * List registered webhooks.
   */
  async listWebhooks(): Promise<{ id: string; url: string; events: string[]; is_active: boolean }[]> {
    const response = await this.client.get('/webhooks')
    return response.data
  }

  /**
   * Delete a webhook.
   */
  async deleteWebhook(webhookId: string): Promise<void> {
    await this.client.delete(`/webhooks/${webhookId}`)
  }

  // ============================================
  // Notifications
  // ============================================

  /**
   * Get user notifications.
   */
  async getNotifications(options?: {
    unread_only?: boolean
    page?: number
    limit?: number
  }): Promise<{ items: Notification[]; total: number; unread_count: number }> {
    const response = await this.client.get('/notifications', { params: options })
    return response.data
  }

  /**
   * Mark notification as read.
   */
  async markNotificationRead(notificationId: string): Promise<void> {
    await this.client.patch(`/notifications/${notificationId}/read`)
  }

  /**
   * Mark all notifications as read.
   */
  async markAllNotificationsRead(): Promise<void> {
    await this.client.post('/notifications/mark-all-read')
  }

  // ============================================
  // Health & Status
  // ============================================

  /**
   * Check API health.
   */
  async healthCheck(): Promise<{
    status: string
    version: string
    timestamp: string
  }> {
    const response = await this.client.get('/health')
    return response.data
  }
}

/**
 * Notification type for SDK
 */
interface Notification {
  id: string
  type: string
  title: string
  message: string
  action_url?: string
  is_read: boolean
  created_at: string
}

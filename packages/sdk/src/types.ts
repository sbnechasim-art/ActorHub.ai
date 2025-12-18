/**
 * ActorHub SDK Types
 */

export interface ActorHubConfig {
  apiKey: string
  baseUrl?: string
  timeout?: number
}

export interface Identity {
  id: string
  user_id: string
  display_name: string
  status: IdentityStatus
  protection_level: ProtectionLevel
  profile_image_url?: string
  is_verified: boolean
  verified_at?: string
  blockchain_hash?: string
  blockchain_tx_id?: string
  allow_commercial: boolean
  allow_ai_training: boolean
  blocked_categories: string[]
  created_at: string
  updated_at: string
}

export type IdentityStatus = 'pending' | 'verified' | 'suspended' | 'deleted'
export type ProtectionLevel = 'free' | 'pro' | 'enterprise'

export interface VerifyRequest {
  image: string | Buffer
  threshold?: number
  include_metadata?: boolean
}

export interface VerifyResponse {
  matched: boolean
  identity_id?: string
  confidence: number
  similarity_score: number
  is_authorized: boolean
  license_info?: LicenseInfo
  metadata?: VerifyMetadata
}

export interface VerifyMetadata {
  processing_time_ms: number
  face_detected: boolean
  face_quality: number
  liveness_score?: number
}

export interface LicenseInfo {
  license_id: string
  license_type: string
  usage_type: string
  valid_until: string
  remaining_uses?: number
}

export interface RegisterRequest {
  face_image: string | Buffer
  verification_image: string | Buffer
  display_name: string
  protection_level?: ProtectionLevel
  allow_commercial?: boolean
  allow_ai_training?: boolean
  blocked_categories?: string[]
}

export interface RegisterResponse {
  identity: Identity
  verification_status: string
  actor_pack_status: string
}

export interface ActorPack {
  id: string
  identity_id: string
  version: string
  status: TrainingStatus
  quality_score?: number
  components: ActorPackComponents
  download_url?: string
  created_at: string
}

export type TrainingStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface ActorPackComponents {
  face: boolean
  voice: boolean
  motion: boolean
}

export interface Listing {
  id: string
  identity_id: string
  title: string
  description: string
  category: string
  pricing_tiers: PricingTier[]
  is_active: boolean
  avg_rating?: number
  rating_count: number
  license_count: number
}

export interface PricingTier {
  name: string
  price: number
  usage_limit?: number
  features: string[]
}

export interface License {
  id: string
  listing_id: string
  buyer_id: string
  identity_id: string
  license_type: string
  usage_type: string
  valid_from: string
  valid_until: string
  usage_count: number
  usage_limit?: number
  is_active: boolean
}

export interface PurchaseLicenseRequest {
  listing_id: string
  tier_name: string
  usage_type: 'personal' | 'commercial' | 'enterprise'
}

export interface UsageLog {
  id: string
  identity_id: string
  license_id?: string
  action: string
  platform?: string
  ip_address?: string
  is_authorized: boolean
  created_at: string
}

export interface DashboardStats {
  identities_count: number
  total_revenue: number
  verification_checks: number
  active_licenses: number
  monthly_trend: number
}

export interface SDKError extends Error {
  code: string
  status?: number
  details?: Record<string, unknown>
}

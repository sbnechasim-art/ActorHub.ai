/**
 * ActorHub.ai Official SDK
 *
 * @packageDocumentation
 * @module @actorhub/sdk
 *
 * @example
 * ```typescript
 * import { ActorHub } from '@actorhub/sdk'
 *
 * const client = new ActorHub({ apiKey: 'your-api-key' })
 *
 * // Verify an image against registered identities
 * const result = await client.verify({
 *   image: imageBuffer, // or base64 string
 *   threshold: 0.85
 * })
 *
 * if (result.matched) {
 *   console.log(`Matched identity: ${result.identity_id}`)
 *   console.log(`Authorized: ${result.is_authorized}`)
 * }
 * ```
 */

export { ActorHubClient } from './client'
export { ActorHubClient as ActorHub } from './client'

export type {
  ActorHubConfig,
  Identity,
  IdentityStatus,
  ProtectionLevel,
  VerifyRequest,
  VerifyResponse,
  VerifyMetadata,
  LicenseInfo,
  RegisterRequest,
  RegisterResponse,
  ActorPack,
  TrainingStatus,
  ActorPackComponents,
  Listing,
  PricingTier,
  License,
  PurchaseLicenseRequest,
  UsageLog,
  DashboardStats,
  SDKError,
} from './types'

// Version
export const VERSION = '1.0.0'

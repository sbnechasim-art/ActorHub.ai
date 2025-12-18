# @actorhub/sdk

Official SDK for ActorHub.ai - Digital Identity Protection Platform

## Installation

```bash
npm install @actorhub/sdk
# or
yarn add @actorhub/sdk
# or
pnpm add @actorhub/sdk
```

## Quick Start

```typescript
import { ActorHub } from '@actorhub/sdk'

const client = new ActorHub({
  apiKey: 'your-api-key',
  // baseUrl: 'https://api.actorhub.ai/v1' // optional
})

// Verify an image
const result = await client.verify({
  image: imageBuffer, // Buffer or base64 string
  threshold: 0.85
})

if (result.matched) {
  console.log(`Identity: ${result.identity_id}`)
  console.log(`Authorized: ${result.is_authorized}`)
  console.log(`Confidence: ${result.confidence}`)
}
```

## API Reference

### Verification

```typescript
// Single image verification
const result = await client.verify({
  image: imageBuffer,
  threshold: 0.85,
  include_metadata: true
})

// Batch verification
const results = await client.verifyBatch([image1, image2, image3])
```

### Identity Management

```typescript
// Register new identity
const identity = await client.registerIdentity({
  face_image: faceImageBuffer,
  verification_image: selfieBuffer,
  display_name: 'John Doe',
  protection_level: 'pro',
  allow_commercial: true
})

// Get my identities
const identities = await client.getMyIdentities()

// Update identity
await client.updateIdentity(identityId, {
  allow_commercial: false
})
```

### Actor Packs

```typescript
// Get Actor Pack
const pack = await client.getActorPack(identityId)

// Train Actor Pack with voice
await client.trainActorPack(identityId, {
  include_voice: true,
  audio_urls: ['https://...']
})

// Download Actor Pack
const { url } = await client.getActorPackDownload(packId)
```

### Marketplace

```typescript
// Browse listings
const { items } = await client.getListings({
  category: 'actor',
  sort: 'popular'
})

// Purchase license
const license = await client.purchaseLicense({
  listing_id: 'listing-123',
  tier_name: 'pro',
  usage_type: 'commercial'
})

// Get my licenses
const licenses = await client.getMyLicenses()
```

## Error Handling

```typescript
import { SDKError } from '@actorhub/sdk'

try {
  await client.verify({ image: buffer })
} catch (error) {
  if (error instanceof SDKError) {
    console.error(`Error: ${error.code}`)
    console.error(`Status: ${error.status}`)
    console.error(`Details: ${JSON.stringify(error.details)}`)
  }
}
```

## TypeScript Support

Full TypeScript support with comprehensive type definitions:

```typescript
import type {
  Identity,
  VerifyResponse,
  ActorPack,
  License
} from '@actorhub/sdk'
```

## License

MIT

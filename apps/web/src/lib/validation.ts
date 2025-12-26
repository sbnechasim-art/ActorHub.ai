/**
 * Form Validation Utilities
 * Simple, type-safe validation without external dependencies
 */

// =============================================================================
// Types
// =============================================================================

export interface ValidationResult {
  valid: boolean
  errors: Record<string, string>
}

export interface FieldValidator {
  validate: (value: unknown) => string | null  // Returns error message or null if valid
}

// =============================================================================
// Validators
// =============================================================================

export const validators = {
  /**
   * Required field validator
   */
  required: (fieldName: string = 'This field'): FieldValidator => ({
    validate: (value) => {
      if (value === null || value === undefined || value === '') {
        return `${fieldName} is required`
      }
      if (typeof value === 'string' && value.trim() === '') {
        return `${fieldName} is required`
      }
      return null
    },
  }),

  /**
   * Minimum length validator
   */
  minLength: (min: number, fieldName: string = 'This field'): FieldValidator => ({
    validate: (value) => {
      if (typeof value !== 'string') return null
      if (value.length < min) {
        return `${fieldName} must be at least ${min} characters`
      }
      return null
    },
  }),

  /**
   * Maximum length validator
   */
  maxLength: (max: number, fieldName: string = 'This field'): FieldValidator => ({
    validate: (value) => {
      if (typeof value !== 'string') return null
      if (value.length > max) {
        return `${fieldName} must be at most ${max} characters`
      }
      return null
    },
  }),

  /**
   * Email validator
   */
  email: (fieldName: string = 'Email'): FieldValidator => ({
    validate: (value) => {
      if (typeof value !== 'string' || !value) return null
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!emailRegex.test(value)) {
        return `${fieldName} must be a valid email address`
      }
      return null
    },
  }),

  /**
   * URL validator
   */
  url: (fieldName: string = 'URL'): FieldValidator => ({
    validate: (value) => {
      if (typeof value !== 'string' || !value) return null
      try {
        new URL(value)
        return null
      } catch {
        return `${fieldName} must be a valid URL`
      }
    },
  }),

  /**
   * Number range validator
   */
  range: (min: number, max: number, fieldName: string = 'Value'): FieldValidator => ({
    validate: (value) => {
      const num = typeof value === 'number' ? value : parseFloat(String(value))
      if (isNaN(num)) return `${fieldName} must be a number`
      if (num < min || num > max) {
        return `${fieldName} must be between ${min} and ${max}`
      }
      return null
    },
  }),

  /**
   * Pattern (regex) validator
   */
  pattern: (regex: RegExp, message: string): FieldValidator => ({
    validate: (value) => {
      if (typeof value !== 'string' || !value) return null
      if (!regex.test(value)) {
        return message
      }
      return null
    },
  }),

  /**
   * File size validator (in bytes)
   */
  fileSize: (maxBytes: number, fieldName: string = 'File'): FieldValidator => ({
    validate: (value) => {
      if (!(value instanceof File)) return null
      if (value.size > maxBytes) {
        const maxMB = (maxBytes / (1024 * 1024)).toFixed(1)
        return `${fieldName} must be smaller than ${maxMB}MB`
      }
      return null
    },
  }),

  /**
   * File type validator
   */
  fileType: (allowedTypes: string[], fieldName: string = 'File'): FieldValidator => ({
    validate: (value) => {
      if (!(value instanceof File)) return null
      const fileType = value.type.toLowerCase()
      const allowed = allowedTypes.map(t => t.toLowerCase())
      if (!allowed.some(t => fileType.includes(t) || fileType === t)) {
        return `${fieldName} must be one of: ${allowedTypes.join(', ')}`
      }
      return null
    },
  }),

  /**
   * Custom validator
   */
  custom: (fn: (value: unknown) => string | null): FieldValidator => ({
    validate: fn,
  }),
}

// =============================================================================
// Validation Functions
// =============================================================================

/**
 * Validate a single field with multiple validators
 */
export function validateField(
  value: unknown,
  fieldValidators: FieldValidator[]
): string | null {
  for (const validator of fieldValidators) {
    const error = validator.validate(value)
    if (error) return error
  }
  return null
}

/**
 * Validate an entire form
 */
export function validateForm<T extends Record<string, unknown>>(
  data: T,
  schema: Record<keyof T, FieldValidator[]>
): ValidationResult {
  const errors: Record<string, string> = {}
  let valid = true

  for (const [field, fieldValidators] of Object.entries(schema)) {
    const error = validateField(data[field as keyof T], fieldValidators as FieldValidator[])
    if (error) {
      errors[field] = error
      valid = false
    }
  }

  return { valid, errors }
}

// =============================================================================
// Common Validation Schemas
// =============================================================================

/**
 * Identity registration validation schema
 */
export const identityRegistrationSchema = {
  displayName: [
    validators.required('Display name'),
    validators.minLength(2, 'Display name'),
    validators.maxLength(50, 'Display name'),
  ],
  faceImage: [
    validators.required('Face photo'),
    validators.fileSize(10 * 1024 * 1024, 'Face photo'),
    validators.fileType(['image/jpeg', 'image/png', 'image/webp'], 'Face photo'),
  ],
  verificationImage: [
    validators.required('Verification selfie'),
    validators.fileSize(10 * 1024 * 1024, 'Verification selfie'),
    validators.fileType(['image/jpeg', 'image/png', 'image/webp'], 'Verification selfie'),
  ],
}

/**
 * User profile validation schema
 */
export const userProfileSchema = {
  email: [
    validators.required('Email'),
    validators.email('Email'),
  ],
  displayName: [
    validators.minLength(2, 'Display name'),
    validators.maxLength(50, 'Display name'),
  ],
}

/**
 * Listing creation validation schema
 */
export const listingSchema = {
  title: [
    validators.required('Title'),
    validators.minLength(5, 'Title'),
    validators.maxLength(100, 'Title'),
  ],
  description: [
    validators.required('Description'),
    validators.minLength(20, 'Description'),
    validators.maxLength(2000, 'Description'),
  ],
  price: [
    validators.required('Price'),
    validators.range(0, 100000, 'Price'),
  ],
}

// =============================================================================
// Hebrew Error Messages
// =============================================================================

const hebrewMessages: Record<string, string> = {
  'is required': 'שדה חובה',
  'must be at least': 'חייב להכיל לפחות',
  'must be at most': 'מקסימום',
  'characters': 'תווים',
  'must be a valid email': 'כתובת אימייל לא תקינה',
  'must be a valid URL': 'כתובת URL לא תקינה',
  'must be between': 'חייב להיות בין',
  'must be smaller than': 'חייב להיות קטן מ-',
  'must be one of': 'חייב להיות אחד מ-',
}

/**
 * Translate error message to Hebrew
 */
export function translateError(error: string): string {
  let translated = error
  for (const [eng, heb] of Object.entries(hebrewMessages)) {
    translated = translated.replace(new RegExp(eng, 'gi'), heb)
  }
  return translated
}

/**
 * Validate form and return Hebrew error messages
 */
export function validateFormHebrew<T extends Record<string, unknown>>(
  data: T,
  schema: Record<keyof T, FieldValidator[]>
): ValidationResult {
  const result = validateForm(data, schema)
  const hebrewErrors: Record<string, string> = {}

  for (const [field, error] of Object.entries(result.errors)) {
    hebrewErrors[field] = translateError(error)
  }

  return { valid: result.valid, errors: hebrewErrors }
}

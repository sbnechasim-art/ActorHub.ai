import { describe, it, expect } from 'vitest'
import {
  validators,
  validateField,
  validateForm,
  translateError,
} from '@/lib/validation'

describe('Validators', () => {
  describe('required', () => {
    const validator = validators.required('Field')

    it('should fail for empty string', () => {
      expect(validator.validate('')).toBe('Field is required')
    })

    it('should fail for whitespace only', () => {
      expect(validator.validate('   ')).toBe('Field is required')
    })

    it('should fail for null', () => {
      expect(validator.validate(null)).toBe('Field is required')
    })

    it('should fail for undefined', () => {
      expect(validator.validate(undefined)).toBe('Field is required')
    })

    it('should pass for non-empty string', () => {
      expect(validator.validate('hello')).toBeNull()
    })
  })

  describe('minLength', () => {
    const validator = validators.minLength(3, 'Name')

    it('should fail for short strings', () => {
      expect(validator.validate('ab')).toBe('Name must be at least 3 characters')
    })

    it('should pass for strings at minimum length', () => {
      expect(validator.validate('abc')).toBeNull()
    })

    it('should pass for longer strings', () => {
      expect(validator.validate('abcdef')).toBeNull()
    })
  })

  describe('maxLength', () => {
    const validator = validators.maxLength(5, 'Name')

    it('should fail for long strings', () => {
      expect(validator.validate('abcdef')).toBe('Name must be at most 5 characters')
    })

    it('should pass for strings at maximum length', () => {
      expect(validator.validate('abcde')).toBeNull()
    })

    it('should pass for shorter strings', () => {
      expect(validator.validate('abc')).toBeNull()
    })
  })

  describe('email', () => {
    const validator = validators.email()

    it('should fail for invalid email', () => {
      expect(validator.validate('notanemail')).toBe('Email must be a valid email address')
    })

    it('should fail for email without domain', () => {
      expect(validator.validate('test@')).toBe('Email must be a valid email address')
    })

    it('should pass for valid email', () => {
      expect(validator.validate('test@example.com')).toBeNull()
    })

    it('should skip validation for empty string', () => {
      expect(validator.validate('')).toBeNull()
    })
  })

  describe('range', () => {
    const validator = validators.range(1, 100, 'Price')

    it('should fail for values below minimum', () => {
      expect(validator.validate(0)).toBe('Price must be between 1 and 100')
    })

    it('should fail for values above maximum', () => {
      expect(validator.validate(101)).toBe('Price must be between 1 and 100')
    })

    it('should pass for values in range', () => {
      expect(validator.validate(50)).toBeNull()
    })

    it('should pass for boundary values', () => {
      expect(validator.validate(1)).toBeNull()
      expect(validator.validate(100)).toBeNull()
    })
  })

  describe('pattern', () => {
    const validator = validators.pattern(/^[A-Z]+$/, 'Must be uppercase letters only')

    it('should fail for non-matching strings', () => {
      expect(validator.validate('hello')).toBe('Must be uppercase letters only')
    })

    it('should pass for matching strings', () => {
      expect(validator.validate('HELLO')).toBeNull()
    })
  })
})

describe('validateField', () => {
  it('should return first error when multiple validators fail', () => {
    const error = validateField('', [
      validators.required('Name'),
      validators.minLength(3, 'Name'),
    ])
    expect(error).toBe('Name is required')
  })

  it('should return null when all validators pass', () => {
    const error = validateField('John', [
      validators.required('Name'),
      validators.minLength(3, 'Name'),
      validators.maxLength(50, 'Name'),
    ])
    expect(error).toBeNull()
  })
})

describe('validateForm', () => {
  const schema = {
    email: [validators.required('Email'), validators.email()],
    name: [validators.required('Name'), validators.minLength(2, 'Name')],
  }

  it('should return valid: true when all fields are valid', () => {
    const result = validateForm(
      { email: 'test@example.com', name: 'John' },
      schema
    )
    expect(result.valid).toBe(true)
    expect(Object.keys(result.errors)).toHaveLength(0)
  })

  it('should return valid: false with errors when fields are invalid', () => {
    const result = validateForm(
      { email: '', name: 'J' },
      schema
    )
    expect(result.valid).toBe(false)
    expect(result.errors.email).toBe('Email is required')
    expect(result.errors.name).toBe('Name must be at least 2 characters')
  })
})

describe('translateError', () => {
  it('should translate "is required" to Hebrew', () => {
    expect(translateError('Name is required')).toContain('שדה חובה')
  })

  it('should translate "must be at least" to Hebrew', () => {
    expect(translateError('Name must be at least 3 characters')).toContain('חייב להכיל לפחות')
  })

  it('should translate email errors to Hebrew', () => {
    expect(translateError('Email must be a valid email')).toContain('כתובת אימייל לא תקינה')
  })
})

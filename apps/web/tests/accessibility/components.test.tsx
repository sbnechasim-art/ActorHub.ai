import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { axe, expectNoAccessibilityViolations, getViolationSummary } from './axe-helper'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'

describe('Component Accessibility Tests', () => {
  describe('Button Component', () => {
    it('should have no accessibility violations with default props', async () => {
      const { container } = render(<Button>Click me</Button>)
      await expectNoAccessibilityViolations(container)
    })

    it('should have no violations with icon-only button when aria-label provided', async () => {
      const { container } = render(
        <Button aria-label="Close dialog">
          <span aria-hidden="true">×</span>
        </Button>
      )
      await expectNoAccessibilityViolations(container)
    })

    it('should have no violations when disabled', async () => {
      const { container } = render(<Button disabled>Disabled Button</Button>)
      await expectNoAccessibilityViolations(container)
    })

    it('should have no violations in loading state', async () => {
      const { container } = render(<Button loading>Loading...</Button>)
      await expectNoAccessibilityViolations(container)
    })

    it('should have no violations with different variants', async () => {
      const variants = ['default', 'destructive', 'outline', 'secondary', 'ghost', 'link'] as const

      for (const variant of variants) {
        const { container } = render(<Button variant={variant}>{variant} Button</Button>)
        const results = await axe(container)
        expect(results.violations, `Variant ${variant} has violations: ${getViolationSummary(results)}`).toHaveLength(0)
      }
    })
  })

  describe('Input Component', () => {
    it('should have no accessibility violations with label', async () => {
      const { container } = render(
        <div>
          <label htmlFor="test-input">Email</label>
          <Input id="test-input" type="email" />
        </div>
      )
      await expectNoAccessibilityViolations(container)
    })

    it('should have no violations with aria-label', async () => {
      const { container } = render(
        <Input aria-label="Search" type="search" placeholder="Search..." />
      )
      await expectNoAccessibilityViolations(container)
    })

    it('should have no violations when disabled', async () => {
      const { container } = render(
        <div>
          <label htmlFor="disabled-input">Disabled Field</label>
          <Input id="disabled-input" disabled />
        </div>
      )
      await expectNoAccessibilityViolations(container)
    })

    it('should have no violations with aria-describedby for error messages', async () => {
      const { container } = render(
        <div>
          <label htmlFor="error-input">Password</label>
          <Input
            id="error-input"
            type="password"
            aria-invalid="true"
            aria-describedby="error-message"
          />
          <span id="error-message" role="alert">
            Password is required
          </span>
        </div>
      )
      await expectNoAccessibilityViolations(container)
    })

    it('should have no violations with different input types', async () => {
      const types = ['text', 'email', 'password', 'tel', 'url', 'number'] as const

      for (const type of types) {
        const { container } = render(
          <div>
            <label htmlFor={`${type}-input`}>{type} Input</label>
            <Input id={`${type}-input`} type={type} />
          </div>
        )
        const results = await axe(container)
        expect(results.violations, `Input type ${type} has violations`).toHaveLength(0)
      }
    })
  })

  describe('Card Component', () => {
    it('should have no accessibility violations', async () => {
      const { container } = render(
        <Card>
          <CardHeader>
            <CardTitle>Card Title</CardTitle>
            <CardDescription>Card description text</CardDescription>
          </CardHeader>
          <CardContent>
            <p>Card content goes here</p>
          </CardContent>
          <CardFooter>
            <Button>Action</Button>
          </CardFooter>
        </Card>
      )
      await expectNoAccessibilityViolations(container)
    })

    it('should have no violations as article', async () => {
      const { container } = render(
        <Card role="article" aria-labelledby="card-title">
          <CardHeader>
            <CardTitle id="card-title">Article Card</CardTitle>
          </CardHeader>
          <CardContent>
            <p>Article content</p>
          </CardContent>
        </Card>
      )
      await expectNoAccessibilityViolations(container)
    })

    it('should have no violations with interactive content', async () => {
      const { container } = render(
        <Card>
          <CardHeader>
            <CardTitle>Interactive Card</CardTitle>
          </CardHeader>
          <CardContent>
            <label htmlFor="card-input">Name</label>
            <Input id="card-input" />
          </CardContent>
          <CardFooter>
            <Button>Submit</Button>
            <Button variant="outline">Cancel</Button>
          </CardFooter>
        </Card>
      )
      await expectNoAccessibilityViolations(container)
    })
  })

  describe('Form Patterns', () => {
    it('should have no violations for login form pattern', async () => {
      const { container } = render(
        <form aria-label="Login form">
          <div>
            <label htmlFor="login-email">Email</label>
            <Input
              id="login-email"
              type="email"
              autoComplete="email"
              required
            />
          </div>
          <div>
            <label htmlFor="login-password">Password</label>
            <Input
              id="login-password"
              type="password"
              autoComplete="current-password"
              required
            />
          </div>
          <Button type="submit">Sign In</Button>
        </form>
      )
      await expectNoAccessibilityViolations(container)
    })

    it('should have no violations for search form pattern', async () => {
      const { container } = render(
        <form role="search" aria-label="Site search">
          <Input
            type="search"
            aria-label="Search"
            placeholder="Search..."
          />
          <Button type="submit" aria-label="Submit search">
            Search
          </Button>
        </form>
      )
      await expectNoAccessibilityViolations(container)
    })
  })

  describe('Button Groups', () => {
    it('should have no violations for button group', async () => {
      const { container } = render(
        <div role="group" aria-label="Actions">
          <Button>Save</Button>
          <Button variant="outline">Cancel</Button>
          <Button variant="destructive">Delete</Button>
        </div>
      )
      await expectNoAccessibilityViolations(container)
    })
  })

  describe('Color Contrast', () => {
    it('button text should have sufficient contrast', async () => {
      const { container } = render(
        <div>
          <Button variant="default">Primary Button</Button>
          <Button variant="secondary">Secondary Button</Button>
          <Button variant="destructive">Destructive Button</Button>
        </div>
      )
      const results = await axe(container)
      const contrastViolations = results.violations.filter(v => v.id === 'color-contrast')
      expect(contrastViolations).toHaveLength(0)
    })
  })
})

import { configureAxe, toHaveNoViolations } from 'jest-axe'
import { expect } from 'vitest'

// Extend expect with accessibility matchers
expect.extend(toHaveNoViolations)

// Configure axe for our tests
export const axe = configureAxe({
  rules: {
    // Critical rules that should always pass
    'color-contrast': { enabled: true },
    'link-name': { enabled: true },
    'button-name': { enabled: true },
    'image-alt': { enabled: true },
    'label': { enabled: true },
    'aria-roles': { enabled: true },
    'aria-valid-attr': { enabled: true },
    'aria-valid-attr-value': { enabled: true },
    'document-title': { enabled: true },
    'html-has-lang': { enabled: true },
    'landmark-one-main': { enabled: true },

    // Form-related rules
    'form-field-multiple-labels': { enabled: true },
    'autocomplete-valid': { enabled: true },

    // Keyboard navigation rules
    'focus-order-semantics': { enabled: true },
    'tabindex': { enabled: true },

    // Structure rules
    'heading-order': { enabled: true },
    'list': { enabled: true },
    'listitem': { enabled: true },

    // Some rules to disable in specific contexts
    // 'region': { enabled: false }, // Disable if using dialogs that break region
  },
})

// Custom assertion helper
export async function expectNoAccessibilityViolations(container: HTMLElement) {
  const results = await axe(container)
  expect(results).toHaveNoViolations()
}

// Helper to get violation summary
export function getViolationSummary(results: any): string {
  if (!results.violations.length) {
    return 'No accessibility violations found'
  }

  return results.violations
    .map((violation: any) => {
      return `
${violation.id}: ${violation.description}
Impact: ${violation.impact}
Help: ${violation.helpUrl}
Nodes affected: ${violation.nodes.length}
      `.trim()
    })
    .join('\n\n')
}

// Helper to check specific WCAG criteria
export function filterByWCAG(results: any, level: 'wcag2a' | 'wcag2aa' | 'wcag21a' | 'wcag21aa') {
  return {
    ...results,
    violations: results.violations.filter((v: any) =>
      v.tags.includes(level)
    ),
  }
}

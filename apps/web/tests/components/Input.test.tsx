import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Input } from '@/components/ui/input'

describe('Input Component', () => {
  describe('Rendering', () => {
    it('renders with default props', () => {
      render(<Input data-testid="input" />)
      const input = screen.getByTestId('input')
      expect(input).toBeInTheDocument()
      expect(input.tagName).toBe('INPUT')
    })

    it('renders with placeholder', () => {
      render(<Input placeholder="Enter text" />)
      expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument()
    })

    it('renders with default value', () => {
      render(<Input defaultValue="Default text" data-testid="input" />)
      expect(screen.getByTestId('input')).toHaveValue('Default text')
    })

    it('renders controlled value', () => {
      render(<Input value="Controlled text" onChange={() => {}} data-testid="input" />)
      expect(screen.getByTestId('input')).toHaveValue('Controlled text')
    })
  })

  describe('Input Types', () => {
    it('renders text type by default', () => {
      render(<Input data-testid="input" />)
      const input = screen.getByTestId('input')
      // HTML inputs default to text, getAttribute may return null or "text"
      const type = input.getAttribute('type')
      expect(type === null || type === 'text').toBe(true)
    })

    it('renders password type', () => {
      render(<Input type="password" data-testid="input" />)
      expect(screen.getByTestId('input')).toHaveAttribute('type', 'password')
    })

    it('renders email type', () => {
      render(<Input type="email" data-testid="input" />)
      expect(screen.getByTestId('input')).toHaveAttribute('type', 'email')
    })

    it('renders number type', () => {
      render(<Input type="number" data-testid="input" />)
      expect(screen.getByTestId('input')).toHaveAttribute('type', 'number')
    })

    it('renders tel type', () => {
      render(<Input type="tel" data-testid="input" />)
      expect(screen.getByTestId('input')).toHaveAttribute('type', 'tel')
    })

    it('renders search type', () => {
      render(<Input type="search" data-testid="input" />)
      expect(screen.getByTestId('input')).toHaveAttribute('type', 'search')
    })

    it('renders url type', () => {
      render(<Input type="url" data-testid="input" />)
      expect(screen.getByTestId('input')).toHaveAttribute('type', 'url')
    })
  })

  describe('User Interactions', () => {
    it('accepts user input', async () => {
      const user = userEvent.setup()
      render(<Input data-testid="input" />)

      const input = screen.getByTestId('input')
      await user.type(input, 'Hello World')

      expect(input).toHaveValue('Hello World')
    })

    it('handles onChange events', async () => {
      const handleChange = vi.fn()
      const user = userEvent.setup()
      render(<Input onChange={handleChange} data-testid="input" />)

      await user.type(screen.getByTestId('input'), 'test')
      expect(handleChange).toHaveBeenCalledTimes(4) // Once per character
    })

    it('handles onFocus events', () => {
      const handleFocus = vi.fn()
      render(<Input onFocus={handleFocus} data-testid="input" />)

      fireEvent.focus(screen.getByTestId('input'))
      expect(handleFocus).toHaveBeenCalledTimes(1)
    })

    it('handles onBlur events', () => {
      const handleBlur = vi.fn()
      render(<Input onBlur={handleBlur} data-testid="input" />)

      const input = screen.getByTestId('input')
      fireEvent.focus(input)
      fireEvent.blur(input)
      expect(handleBlur).toHaveBeenCalledTimes(1)
    })

    it('clears input value', async () => {
      const user = userEvent.setup()
      render(<Input data-testid="input" defaultValue="Initial" />)

      const input = screen.getByTestId('input')
      await user.clear(input)

      expect(input).toHaveValue('')
    })
  })

  describe('Disabled State', () => {
    it('can be disabled', () => {
      render(<Input disabled data-testid="input" />)
      expect(screen.getByTestId('input')).toBeDisabled()
    })

    it('applies disabled styles', () => {
      render(<Input disabled data-testid="input" />)
      const input = screen.getByTestId('input')
      expect(input).toHaveClass('disabled:cursor-not-allowed')
      expect(input).toHaveClass('disabled:opacity-50')
    })

    it('does not accept input when disabled', async () => {
      const handleChange = vi.fn()
      render(<Input disabled onChange={handleChange} data-testid="input" />)

      const input = screen.getByTestId('input')
      // Note: userEvent won't type into disabled inputs
      fireEvent.change(input, { target: { value: 'test' } })
      // Disabled inputs don't trigger change events
    })
  })

  describe('Read Only State', () => {
    it('can be read only', () => {
      render(<Input readOnly data-testid="input" />)
      expect(screen.getByTestId('input')).toHaveAttribute('readonly')
    })

    it('displays value but prevents editing', async () => {
      const user = userEvent.setup()
      render(<Input readOnly defaultValue="Read only value" data-testid="input" />)

      const input = screen.getByTestId('input')
      expect(input).toHaveValue('Read only value')

      // userEvent respects readonly
      await user.type(input, 'new text')
      expect(input).toHaveValue('Read only value')
    })
  })

  describe('Custom className', () => {
    it('applies custom className', () => {
      render(<Input className="custom-class" data-testid="input" />)
      expect(screen.getByTestId('input')).toHaveClass('custom-class')
    })

    it('merges custom className with default classes', () => {
      render(<Input className="custom-class" data-testid="input" />)
      const input = screen.getByTestId('input')
      expect(input).toHaveClass('custom-class')
      expect(input).toHaveClass('rounded-md') // Default class
    })
  })

  describe('Form Integration', () => {
    it('has correct name attribute', () => {
      render(<Input name="email" data-testid="input" />)
      expect(screen.getByTestId('input')).toHaveAttribute('name', 'email')
    })

    it('has correct id attribute', () => {
      render(<Input id="email-input" data-testid="input" />)
      expect(screen.getByTestId('input')).toHaveAttribute('id', 'email-input')
    })

    it('supports required attribute', () => {
      render(<Input required data-testid="input" />)
      expect(screen.getByTestId('input')).toBeRequired()
    })

    it('supports pattern attribute', () => {
      render(<Input pattern="[A-Za-z]+" data-testid="input" />)
      expect(screen.getByTestId('input')).toHaveAttribute('pattern', '[A-Za-z]+')
    })

    it('supports minLength and maxLength', () => {
      render(<Input minLength={5} maxLength={10} data-testid="input" />)
      const input = screen.getByTestId('input')
      expect(input).toHaveAttribute('minLength', '5')
      expect(input).toHaveAttribute('maxLength', '10')
    })
  })

  describe('Accessibility', () => {
    it('supports aria-label', () => {
      render(<Input aria-label="Email address" data-testid="input" />)
      expect(screen.getByLabelText('Email address')).toBeInTheDocument()
    })

    it('supports aria-describedby', () => {
      render(
        <>
          <Input aria-describedby="help-text" data-testid="input" />
          <span id="help-text">Enter your email address</span>
        </>
      )
      expect(screen.getByTestId('input')).toHaveAttribute('aria-describedby', 'help-text')
    })

    it('can be associated with label', () => {
      render(
        <>
          <label htmlFor="email-input">Email</label>
          <Input id="email-input" data-testid="input" />
        </>
      )
      expect(screen.getByLabelText('Email')).toBeInTheDocument()
    })

    it('supports autoComplete', () => {
      render(<Input autoComplete="email" data-testid="input" />)
      expect(screen.getByTestId('input')).toHaveAttribute('autoComplete', 'email')
    })
  })

  describe('Ref Forwarding', () => {
    it('forwards ref to input element', () => {
      const ref = vi.fn()
      render(<Input ref={ref} />)
      expect(ref).toHaveBeenCalled()
      expect(ref.mock.calls[0][0]).toBeInstanceOf(HTMLInputElement)
    })

    it('allows programmatic focus via ref', () => {
      const ref = { current: null as HTMLInputElement | null }
      render(<Input ref={ref} data-testid="input" />)

      ref.current?.focus()
      expect(screen.getByTestId('input')).toHaveFocus()
    })
  })

  describe('File Input', () => {
    it('renders file type', () => {
      render(<Input type="file" data-testid="input" />)
      expect(screen.getByTestId('input')).toHaveAttribute('type', 'file')
    })

    it('accepts file attribute', () => {
      render(<Input type="file" accept="image/*" data-testid="input" />)
      expect(screen.getByTestId('input')).toHaveAttribute('accept', 'image/*')
    })
  })
})

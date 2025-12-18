import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui/card'

describe('Card Component', () => {
  describe('Card', () => {
    it('renders with children', () => {
      render(<Card>Card content</Card>)
      expect(screen.getByText('Card content')).toBeInTheDocument()
    })

    it('applies default classes', () => {
      render(<Card data-testid="card">Content</Card>)
      const card = screen.getByTestId('card')
      expect(card).toHaveClass('rounded-xl')
      expect(card).toHaveClass('border')
      expect(card).toHaveClass('shadow')
    })

    it('applies custom className', () => {
      render(<Card className="custom-class" data-testid="card">Content</Card>)
      expect(screen.getByTestId('card')).toHaveClass('custom-class')
    })

    it('merges custom className with default classes', () => {
      render(<Card className="custom-class" data-testid="card">Content</Card>)
      const card = screen.getByTestId('card')
      expect(card).toHaveClass('custom-class')
      expect(card).toHaveClass('rounded-xl')
    })

    it('passes through HTML attributes', () => {
      render(<Card data-testid="card" id="my-card" role="article">Content</Card>)
      const card = screen.getByTestId('card')
      expect(card).toHaveAttribute('id', 'my-card')
      expect(card).toHaveAttribute('role', 'article')
    })
  })

  describe('CardHeader', () => {
    it('renders with children', () => {
      render(<CardHeader>Header content</CardHeader>)
      expect(screen.getByText('Header content')).toBeInTheDocument()
    })

    it('applies default classes', () => {
      render(<CardHeader data-testid="header">Content</CardHeader>)
      const header = screen.getByTestId('header')
      expect(header).toHaveClass('flex')
      expect(header).toHaveClass('flex-col')
      expect(header).toHaveClass('p-6')
    })

    it('applies custom className', () => {
      render(<CardHeader className="custom-header" data-testid="header">Content</CardHeader>)
      expect(screen.getByTestId('header')).toHaveClass('custom-header')
    })
  })

  describe('CardTitle', () => {
    it('renders as h3 element', () => {
      render(<CardTitle>Title</CardTitle>)
      const title = screen.getByRole('heading', { level: 3 })
      expect(title).toBeInTheDocument()
      expect(title).toHaveTextContent('Title')
    })

    it('applies default classes', () => {
      render(<CardTitle data-testid="title">Title</CardTitle>)
      const title = screen.getByTestId('title')
      expect(title).toHaveClass('font-semibold')
      expect(title).toHaveClass('leading-none')
      expect(title).toHaveClass('tracking-tight')
    })

    it('applies custom className', () => {
      render(<CardTitle className="custom-title" data-testid="title">Title</CardTitle>)
      expect(screen.getByTestId('title')).toHaveClass('custom-title')
    })
  })

  describe('CardDescription', () => {
    it('renders as p element', () => {
      render(<CardDescription>Description text</CardDescription>)
      expect(screen.getByText('Description text').tagName).toBe('P')
    })

    it('applies default classes', () => {
      render(<CardDescription data-testid="description">Description</CardDescription>)
      const description = screen.getByTestId('description')
      expect(description).toHaveClass('text-sm')
      expect(description).toHaveClass('text-muted-foreground')
    })

    it('applies custom className', () => {
      render(
        <CardDescription className="custom-description" data-testid="description">
          Description
        </CardDescription>
      )
      expect(screen.getByTestId('description')).toHaveClass('custom-description')
    })
  })

  describe('CardContent', () => {
    it('renders with children', () => {
      render(<CardContent>Content goes here</CardContent>)
      expect(screen.getByText('Content goes here')).toBeInTheDocument()
    })

    it('applies default classes', () => {
      render(<CardContent data-testid="content">Content</CardContent>)
      const content = screen.getByTestId('content')
      expect(content).toHaveClass('p-6')
      expect(content).toHaveClass('pt-0')
    })

    it('applies custom className', () => {
      render(<CardContent className="custom-content" data-testid="content">Content</CardContent>)
      expect(screen.getByTestId('content')).toHaveClass('custom-content')
    })
  })

  describe('CardFooter', () => {
    it('renders with children', () => {
      render(<CardFooter>Footer content</CardFooter>)
      expect(screen.getByText('Footer content')).toBeInTheDocument()
    })

    it('applies default classes', () => {
      render(<CardFooter data-testid="footer">Footer</CardFooter>)
      const footer = screen.getByTestId('footer')
      expect(footer).toHaveClass('flex')
      expect(footer).toHaveClass('items-center')
      expect(footer).toHaveClass('p-6')
      expect(footer).toHaveClass('pt-0')
    })

    it('applies custom className', () => {
      render(<CardFooter className="custom-footer" data-testid="footer">Footer</CardFooter>)
      expect(screen.getByTestId('footer')).toHaveClass('custom-footer')
    })
  })

  describe('Complete Card Structure', () => {
    it('renders complete card with all sections', () => {
      render(
        <Card data-testid="card">
          <CardHeader data-testid="header">
            <CardTitle data-testid="title">Card Title</CardTitle>
            <CardDescription data-testid="description">Card description text</CardDescription>
          </CardHeader>
          <CardContent data-testid="content">
            <p>Card content goes here</p>
          </CardContent>
          <CardFooter data-testid="footer">
            <button>Action</button>
          </CardFooter>
        </Card>
      )

      expect(screen.getByTestId('card')).toBeInTheDocument()
      expect(screen.getByTestId('header')).toBeInTheDocument()
      expect(screen.getByTestId('title')).toHaveTextContent('Card Title')
      expect(screen.getByTestId('description')).toHaveTextContent('Card description text')
      expect(screen.getByTestId('content')).toBeInTheDocument()
      expect(screen.getByText('Card content goes here')).toBeInTheDocument()
      expect(screen.getByTestId('footer')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument()
    })

    it('renders card without optional sections', () => {
      render(
        <Card data-testid="card">
          <CardContent data-testid="content">Only content</CardContent>
        </Card>
      )
      expect(screen.getByTestId('card')).toBeInTheDocument()
      expect(screen.getByText('Only content')).toBeInTheDocument()
    })

    it('renders card with only header', () => {
      render(
        <Card data-testid="card">
          <CardHeader>
            <CardTitle>Header Only Card</CardTitle>
          </CardHeader>
        </Card>
      )
      expect(screen.getByText('Header Only Card')).toBeInTheDocument()
    })

    it('renders nested content correctly', () => {
      render(
        <Card>
          <CardContent>
            <div data-testid="nested-div">
              <span data-testid="nested-span">Nested content</span>
            </div>
          </CardContent>
        </Card>
      )
      expect(screen.getByTestId('nested-div')).toBeInTheDocument()
      expect(screen.getByTestId('nested-span')).toHaveTextContent('Nested content')
    })
  })

  describe('Accessibility', () => {
    it('supports custom role', () => {
      render(<Card role="region" data-testid="card">Content</Card>)
      expect(screen.getByTestId('card')).toHaveAttribute('role', 'region')
    })

    it('supports aria-label', () => {
      render(<Card aria-label="Important card" data-testid="card">Content</Card>)
      expect(screen.getByLabelText('Important card')).toBeInTheDocument()
    })

    it('title is semantic heading', () => {
      render(
        <Card>
          <CardHeader>
            <CardTitle>Accessible Title</CardTitle>
          </CardHeader>
        </Card>
      )
      expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Accessible Title')
    })
  })

  describe('Ref Forwarding', () => {
    it('Card forwards ref', () => {
      const ref = { current: null as HTMLDivElement | null }
      render(<Card ref={ref} data-testid="card">Content</Card>)
      expect(ref.current).toBeInstanceOf(HTMLDivElement)
    })

    it('CardHeader forwards ref', () => {
      const ref = { current: null as HTMLDivElement | null }
      render(<CardHeader ref={ref} data-testid="header">Content</CardHeader>)
      expect(ref.current).toBeInstanceOf(HTMLDivElement)
    })

    it('CardContent forwards ref', () => {
      const ref = { current: null as HTMLDivElement | null }
      render(<CardContent ref={ref} data-testid="content">Content</CardContent>)
      expect(ref.current).toBeInstanceOf(HTMLDivElement)
    })

    it('CardFooter forwards ref', () => {
      const ref = { current: null as HTMLDivElement | null }
      render(<CardFooter ref={ref} data-testid="footer">Content</CardFooter>)
      expect(ref.current).toBeInstanceOf(HTMLDivElement)
    })
  })
})

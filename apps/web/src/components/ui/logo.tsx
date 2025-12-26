'use client'

import Image from 'next/image'
import Link from 'next/link'
import { cn } from '@/lib/utils'

/**
 * Logo Component - ActorHub.ai
 *
 * Adaptive, professional, and modular logo component
 * Supports: full (icon + text), icon-only, and auto (responsive) variants
 */

export type LogoVariant = 'full' | 'icon' | 'auto'
export type LogoSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl'

interface LogoProps {
  /** Logo variant: 'full' (icon + text), 'icon' (icon only), 'auto' (responsive) */
  variant?: LogoVariant
  /** Size preset */
  size?: LogoSize
  /** Link destination (default: '/') */
  href?: string
  /** Additional class names */
  className?: string
  /** Show text alongside icon (only when variant is 'full' or 'auto') */
  showText?: boolean
  /** Custom click handler (overrides link behavior) */
  onClick?: () => void
  /** Disable link behavior */
  asDiv?: boolean
  /** Show glow effect */
  glow?: boolean
}

// Size configurations - increased for better visibility
const sizeConfig: Record<LogoSize, { icon: number; text: string; gap: string }> = {
  xs: { icon: 24, text: 'text-base', gap: 'gap-1.5' },
  sm: { icon: 32, text: 'text-lg', gap: 'gap-2' },
  md: { icon: 40, text: 'text-xl', gap: 'gap-2.5' },
  lg: { icon: 56, text: 'text-2xl', gap: 'gap-3' },
  xl: { icon: 72, text: 'text-3xl', gap: 'gap-3' },
  '2xl': { icon: 96, text: 'text-4xl', gap: 'gap-4' },
  '3xl': { icon: 140, text: 'text-5xl', gap: 'gap-5' },
}

export function Logo({
  variant = 'auto',
  size = 'md',
  href = '/',
  className,
  showText = true,
  onClick,
  asDiv = false,
  glow = false,
}: LogoProps) {
  const config = sizeConfig[size]

  const content = (
    <>
      {/* Logo Icon */}
      <div
        className={cn(
          "relative flex-shrink-0",
          glow && "drop-shadow-[0_0_15px_rgba(59,130,246,0.5)]"
        )}
        style={{ width: config.icon, height: config.icon }}
      >
        <Image
          src="/logo.png"
          alt="ActorHub.ai"
          fill
          className="object-contain"
          priority
        />
      </div>

      {/* Logo Text - conditionally rendered based on variant */}
      {showText && (
        <span
          className={cn(
            'font-bold text-white whitespace-nowrap transition-opacity duration-200',
            config.text,
            // Auto variant: hide on mobile, show on desktop
            variant === 'auto' && 'hidden md:inline',
            // Icon variant: always hidden
            variant === 'icon' && 'hidden',
            // Full variant: always visible
            variant === 'full' && 'inline'
          )}
        >
          <span className="bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
            ActorHub
          </span>
          <span className="text-purple-400">.ai</span>
        </span>
      )}
    </>
  )

  const containerClasses = cn(
    'flex items-center',
    config.gap,
    'transition-transform hover:scale-[1.02] active:scale-[0.98]',
    className
  )

  // Render as div if specified or no href
  if (asDiv || !href) {
    return (
      <div className={containerClasses} onClick={onClick}>
        {content}
      </div>
    )
  }

  // Render as link
  return (
    <Link href={href} className={containerClasses} onClick={onClick}>
      {content}
    </Link>
  )
}

/**
 * Logo Icon Only - Convenience component for icon-only usage
 */
export function LogoIcon({
  size = 'md',
  className,
  ...props
}: Omit<LogoProps, 'variant' | 'showText'>) {
  return (
    <Logo
      variant="icon"
      showText={false}
      size={size}
      className={className}
      {...props}
    />
  )
}

/**
 * Logo Full - Convenience component for full logo usage
 */
export function LogoFull({
  size = 'md',
  className,
  ...props
}: Omit<LogoProps, 'variant'>) {
  return (
    <Logo
      variant="full"
      size={size}
      className={className}
      {...props}
    />
  )
}

/**
 * Hero Logo - Large logo for landing pages and auth screens
 */
export function LogoHero({
  className,
  ...props
}: Omit<LogoProps, 'variant' | 'size'>) {
  return (
    <Logo
      variant="full"
      size="2xl"
      glow
      className={className}
      {...props}
    />
  )
}

export default Logo

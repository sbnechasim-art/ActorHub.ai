'use client'

import { cn } from '@/lib/utils'

interface FaceGuideOverlayProps {
  className?: string
  isPositioned?: boolean // True when face is well-positioned
}

export function FaceGuideOverlay({ className, isPositioned = false }: FaceGuideOverlayProps) {
  return (
    <div className={cn('absolute inset-0 pointer-events-none', className)}>
      <svg
        className="w-full h-full"
        viewBox="0 0 100 100"
        preserveAspectRatio="xMidYMid slice"
      >
        {/* Dark overlay with transparent oval cutout */}
        <defs>
          <mask id="faceMask">
            <rect x="0" y="0" width="100" height="100" fill="white" />
            <ellipse
              cx="50"
              cy="45"
              rx="22"
              ry="30"
              fill="black"
            />
          </mask>
        </defs>

        {/* Semi-transparent overlay */}
        <rect
          x="0"
          y="0"
          width="100"
          height="100"
          fill="rgba(0, 0, 0, 0.5)"
          mask="url(#faceMask)"
        />

        {/* Face guide oval border */}
        <ellipse
          cx="50"
          cy="45"
          rx="22"
          ry="30"
          fill="none"
          stroke={isPositioned ? '#22c55e' : '#ffffff'}
          strokeWidth="0.5"
          strokeDasharray={isPositioned ? '0' : '2 1'}
          className="transition-all duration-300"
        />

        {/* Corner guides */}
        <g stroke={isPositioned ? '#22c55e' : '#ffffff'} strokeWidth="0.4" fill="none">
          {/* Top left */}
          <path d="M 28 20 L 28 15 L 33 15" />
          {/* Top right */}
          <path d="M 72 20 L 72 15 L 67 15" />
          {/* Bottom left */}
          <path d="M 28 70 L 28 75 L 33 75" />
          {/* Bottom right */}
          <path d="M 72 70 L 72 75 L 67 75" />
        </g>
      </svg>

      {/* Instruction text at bottom */}
      <div className="absolute bottom-4 left-0 right-0 text-center">
        <p className={cn(
          'text-sm font-medium px-4 py-2 rounded-full inline-block',
          isPositioned
            ? 'bg-green-500/20 text-green-400'
            : 'bg-black/40 text-white'
        )}>
          {isPositioned ? 'Perfect! Hold still' : 'Position your face in the oval'}
        </p>
      </div>
    </div>
  )
}

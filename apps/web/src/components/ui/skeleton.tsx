import { cn } from '@/lib/utils'

interface SkeletonProps {
  className?: string
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-slate-700/50',
        className
      )}
    />
  )
}

// Common skeleton patterns
export function SkeletonCard({ className }: SkeletonProps) {
  return (
    <div className={cn('rounded-lg border border-slate-700 bg-slate-800/50 p-6', className)}>
      <div className="space-y-4">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <div className="pt-4">
          <Skeleton className="h-20 w-full" />
        </div>
      </div>
    </div>
  )
}

export function SkeletonAvatar({ className }: SkeletonProps) {
  return (
    <Skeleton className={cn('h-12 w-12 rounded-full', className)} />
  )
}

export function SkeletonButton({ className }: SkeletonProps) {
  return (
    <Skeleton className={cn('h-10 w-24 rounded-md', className)} />
  )
}

export function SkeletonText({ lines = 3, className }: SkeletonProps & { lines?: number }) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn('h-4', i === lines - 1 ? 'w-2/3' : 'w-full')}
        />
      ))}
    </div>
  )
}

// Dashboard skeleton
export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <SkeletonCard key={i} />
        ))}
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SkeletonCard className="h-64" />
        <SkeletonCard className="h-64" />
      </div>
    </div>
  )
}

// Identity card skeleton
export function IdentityCardSkeleton() {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
      <div className="flex items-center gap-4">
        <SkeletonAvatar className="h-16 w-16" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-24" />
        </div>
        <SkeletonButton />
      </div>
    </div>
  )
}

// Marketplace listing skeleton
export function ListingSkeleton() {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/50 overflow-hidden">
      <Skeleton className="h-48 w-full rounded-none" />
      <div className="p-4 space-y-3">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <div className="flex justify-between items-center pt-2">
          <Skeleton className="h-6 w-20" />
          <SkeletonButton />
        </div>
      </div>
    </div>
  )
}

// Table row skeleton
export function TableRowSkeleton({ columns = 4 }: { columns?: number }) {
  return (
    <tr className="border-b border-slate-700">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="p-4">
          <Skeleton className="h-4 w-full" />
        </td>
      ))}
    </tr>
  )
}

// Full page loading
export function PageLoadingSkeleton() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <div className="flex gap-4">
            <SkeletonButton />
            <SkeletonButton />
          </div>
        </div>

        {/* Content */}
        <DashboardSkeleton />
      </div>
    </div>
  )
}

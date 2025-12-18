'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import {
  Bell,
  BellOff,
  Check,
  CheckCheck,
  Filter,
  AlertCircle,
  CreditCard,
  Shield,
  Megaphone,
  Settings,
  Zap,
  Search as SearchIcon,
  RefreshCw,
  Loader2,
  ChevronRight,
  Clock,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { notificationsApi, Notification } from '@/lib/api'
import { cn, formatRelativeTime } from '@/lib/utils'

type NotificationType = 'SYSTEM' | 'MARKETING' | 'SECURITY' | 'BILLING' | 'IDENTITY' | 'TRAINING' | 'DETECTION'

const NOTIFICATION_TYPE_CONFIG: Record<
  NotificationType,
  { label: string; icon: typeof Bell; color: string; bgColor: string }
> = {
  SYSTEM: {
    label: 'System',
    icon: Settings,
    color: 'text-slate-400',
    bgColor: 'bg-slate-500/10',
  },
  MARKETING: {
    label: 'Marketing',
    icon: Megaphone,
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10',
  },
  SECURITY: {
    label: 'Security',
    icon: Shield,
    color: 'text-red-400',
    bgColor: 'bg-red-500/10',
  },
  BILLING: {
    label: 'Billing',
    icon: CreditCard,
    color: 'text-green-400',
    bgColor: 'bg-green-500/10',
  },
  IDENTITY: {
    label: 'Identity',
    icon: Bell,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
  },
  TRAINING: {
    label: 'Training',
    icon: Zap,
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/10',
  },
  DETECTION: {
    label: 'Detection',
    icon: AlertCircle,
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/10',
  },
}

const FILTER_OPTIONS = [
  { value: '', label: 'All Notifications' },
  { value: 'SYSTEM', label: 'System' },
  { value: 'SECURITY', label: 'Security' },
  { value: 'BILLING', label: 'Billing' },
  { value: 'IDENTITY', label: 'Identity' },
  { value: 'TRAINING', label: 'Training' },
  { value: 'DETECTION', label: 'Detection' },
]

export default function NotificationsPage() {
  const queryClient = useQueryClient()
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [showUnreadOnly, setShowUnreadOnly] = useState(false)

  // Fetch notifications
  const {
    data: notificationsData,
    isLoading,
    error,
    refetch,
    isRefetching,
  } = useQuery({
    queryKey: ['notifications', typeFilter, showUnreadOnly],
    queryFn: () =>
      notificationsApi.getAll({
        type: typeFilter || undefined,
        is_read: showUnreadOnly ? false : undefined,
        limit: 100,
      }),
  })

  const notifications = notificationsData?.notifications || []
  const unreadCount = notificationsData?.unread_count || 0

  // Mark single notification as read
  const markAsReadMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.markAsRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  // Mark all as read
  const markAllAsReadMutation = useMutation({
    mutationFn: () => notificationsApi.markAllAsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  // Delete notification
  const deleteNotificationMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  // Group notifications by date
  const groupNotificationsByDate = (notifications: Notification[]) => {
    const groups: Record<string, Notification[]> = {}

    notifications.forEach((notification) => {
      const date = new Date(notification.created_at)
      const today = new Date()
      const yesterday = new Date(today)
      yesterday.setDate(yesterday.getDate() - 1)

      let key: string
      if (date.toDateString() === today.toDateString()) {
        key = 'Today'
      } else if (date.toDateString() === yesterday.toDateString()) {
        key = 'Yesterday'
      } else {
        key = date.toLocaleDateString('en-US', {
          weekday: 'long',
          month: 'short',
          day: 'numeric',
        })
      }

      if (!groups[key]) {
        groups[key] = []
      }
      groups[key].push(notification)
    })

    return groups
  }

  const groupedNotifications = groupNotificationsByDate(notifications)

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
        <header className="border-b border-slate-800">
          <div className="container mx-auto px-4 h-16 flex items-center">
            <div className="h-6 w-40 bg-slate-800 rounded animate-pulse" />
          </div>
        </header>
        <main className="container mx-auto px-4 py-8 max-w-3xl">
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-24 bg-slate-800/50 rounded-xl animate-pulse" />
            ))}
          </div>
        </main>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <Card className="bg-slate-800/50 border-slate-700 max-w-md">
          <CardContent className="p-8 text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Failed to Load Notifications</h2>
            <p className="text-slate-400 mb-6">
              We couldn't load your notifications. Please try again.
            </p>
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Try Again
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bell className="w-6 h-6 text-blue-500" />
            <h1 className="text-xl font-semibold text-white">Notifications</h1>
            {unreadCount > 0 && (
              <span className="px-2 py-0.5 text-xs font-medium bg-blue-500 text-white rounded-full">
                {unreadCount} new
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => refetch()}
              disabled={isRefetching}
            >
              <RefreshCw className={cn('w-4 h-4', isRefetching && 'animate-spin')} />
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link href="/settings">
                <Settings className="w-4 h-4 mr-2" />
                Preferences
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-3xl">
        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          {/* Type Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-500" />
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="h-10 rounded-md border bg-slate-800 border-slate-700 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {FILTER_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Unread Only Toggle */}
          <button
            onClick={() => setShowUnreadOnly(!showUnreadOnly)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
              showUnreadOnly
                ? 'bg-blue-500 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            )}
          >
            {showUnreadOnly ? <Bell className="w-4 h-4" /> : <BellOff className="w-4 h-4" />}
            Unread Only
          </button>

          {/* Mark All as Read */}
          {unreadCount > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => markAllAsReadMutation.mutate()}
              disabled={markAllAsReadMutation.isPending}
              className="ml-auto"
            >
              {markAllAsReadMutation.isPending ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <CheckCheck className="w-4 h-4 mr-2" />
              )}
              Mark All Read
            </Button>
          )}
        </div>

        {/* Notifications List */}
        {notifications.length === 0 ? (
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="p-12 text-center">
              <BellOff className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">No Notifications</h3>
              <p className="text-slate-400">
                {showUnreadOnly
                  ? "You're all caught up! No unread notifications."
                  : "You don't have any notifications yet."}
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-8">
            {Object.entries(groupedNotifications).map(([date, dateNotifications]) => (
              <div key={date}>
                {/* Date Header */}
                <div className="flex items-center gap-3 mb-4">
                  <Clock className="w-4 h-4 text-slate-500" />
                  <h2 className="text-sm font-medium text-slate-400">{date}</h2>
                  <div className="flex-1 h-px bg-slate-800" />
                </div>

                {/* Notifications for this date */}
                <div className="space-y-3">
                  {dateNotifications.map((notification) => {
                    const typeConfig =
                      NOTIFICATION_TYPE_CONFIG[notification.type as NotificationType] ||
                      NOTIFICATION_TYPE_CONFIG.SYSTEM
                    const TypeIcon = typeConfig.icon

                    return (
                      <div
                        key={notification.id}
                        className={cn(
                          'group relative p-4 rounded-xl border transition-all',
                          notification.is_read
                            ? 'bg-slate-800/30 border-slate-800'
                            : 'bg-slate-800/50 border-slate-700 shadow-lg'
                        )}
                      >
                        <div className="flex items-start gap-4">
                          {/* Icon */}
                          <div className={cn('p-2 rounded-lg', typeConfig.bgColor)}>
                            <TypeIcon className={cn('w-5 h-5', typeConfig.color)} />
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <h3
                                className={cn(
                                  'font-medium',
                                  notification.is_read ? 'text-slate-400' : 'text-white'
                                )}
                              >
                                {notification.title}
                              </h3>
                              {!notification.is_read && (
                                <span className="w-2 h-2 rounded-full bg-blue-500" />
                              )}
                            </div>
                            <p className="text-sm text-slate-400 mb-2">{notification.message}</p>
                            <div className="flex items-center gap-3 text-xs text-slate-500">
                              <span>{formatRelativeTime(notification.created_at)}</span>
                              <span
                                className={cn(
                                  'px-2 py-0.5 rounded-full',
                                  typeConfig.bgColor,
                                  typeConfig.color
                                )}
                              >
                                {typeConfig.label}
                              </span>
                            </div>
                          </div>

                          {/* Actions */}
                          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            {!notification.is_read && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => markAsReadMutation.mutate(notification.id)}
                                disabled={markAsReadMutation.isPending}
                                title="Mark as read"
                              >
                                <Check className="w-4 h-4" />
                              </Button>
                            )}
                            {notification.action_url && (
                              <Button variant="ghost" size="sm" asChild>
                                <Link href={notification.action_url}>
                                  <ChevronRight className="w-4 h-4" />
                                </Link>
                              </Button>
                            )}
                          </div>
                        </div>

                        {/* Action Link */}
                        {notification.action_url && (
                          <Link
                            href={notification.action_url}
                            className="absolute inset-0 rounded-xl"
                            onClick={() => {
                              if (!notification.is_read) {
                                markAsReadMutation.mutate(notification.id)
                              }
                            }}
                          >
                            <span className="sr-only">View details</span>
                          </Link>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

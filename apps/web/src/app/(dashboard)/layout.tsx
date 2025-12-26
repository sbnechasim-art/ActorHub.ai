'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { Logo } from '@/components/ui/logo'
import { usePathname, useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Shield,
  LayoutDashboard,
  User,
  Store,
  Package,
  Settings,
  LogOut,
  Bell,
  ChevronDown,
  Check,
  X,
  Loader2,
  Eye,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  Cpu,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

// Notification type
interface Notification {
  id: string
  type: 'verification' | 'license' | 'alert' | 'system' | 'training'
  title: string
  message: string
  is_read: boolean
  created_at: string
  action_url?: string
  // Training-specific fields
  training_progress?: number
  training_status?: 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
}

// Notification icon based on type
function NotificationIcon({ type, isAnimated }: { type: Notification['type']; isAnimated?: boolean }) {
  switch (type) {
    case 'verification':
      return <Eye className="w-4 h-4 text-green-400" />
    case 'license':
      return <DollarSign className="w-4 h-4 text-blue-400" />
    case 'alert':
      return <AlertTriangle className="w-4 h-4 text-yellow-400" />
    case 'system':
      return <CheckCircle className="w-4 h-4 text-purple-400" />
    case 'training':
      return <Cpu className={`w-4 h-4 text-cyan-400 ${isAnimated ? 'animate-pulse' : ''}`} />
    default:
      return <Bell className="w-4 h-4 text-slate-400" />
  }
}

// Format relative time
function formatRelativeTime(dateString: string) {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

// Sample notifications (used when API is not available)
const SAMPLE_NOTIFICATIONS: Notification[] = [
  {
    id: '1',
    type: 'verification',
    title: 'Identity Verified',
    message: 'Your identity "John Doe" has been successfully verified.',
    is_read: false,
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    action_url: '/identity/1',
  },
  {
    id: '2',
    type: 'license',
    title: 'New License Purchase',
    message: 'Someone purchased a Pro license for your Actor Pack.',
    is_read: false,
    created_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    action_url: '/dashboard',
  },
  {
    id: '3',
    type: 'alert',
    title: 'Protection Alert',
    message: 'We detected potential unauthorized use of your identity.',
    is_read: false,
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    action_url: '/dashboard/alerts',
  },
]

// Training Progress Mini Component for notifications
function TrainingProgressMini({ progress, status }: { progress: number; status?: string }) {
  return (
    <div className="mt-2">
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span>{status === 'PROCESSING' ? 'מאמן...' : 'ממתין'}</span>
        <span>{progress}%</span>
      </div>
      <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  )
}

// Notifications Dropdown Component
function NotificationsDropdown() {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()

  // Fetch notifications
  const { data: notificationsData, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => {
      try {
        const response = await api.get('/notifications')
        return response.data
      } catch {
        // Return sample data if API fails
        return { notifications: SAMPLE_NOTIFICATIONS, unread_count: 3 }
      }
    },
    refetchInterval: 60000, // Refetch every minute
  })

  const notifications: Notification[] = notificationsData?.notifications || SAMPLE_NOTIFICATIONS
  const unreadCount = notificationsData?.unread_count ?? notifications.filter(n => !n.is_read).length

  // Mark as read mutation
  const markAsReadMutation = useMutation({
    mutationFn: async (notificationId: string) => {
      await api.post(`/notifications/${notificationId}/read`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  // Mark all as read mutation
  const markAllAsReadMutation = useMutation({
    mutationFn: async () => {
      await api.post('/notifications/read-all')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Close on escape
  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [])

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Button */}
      <Button
        variant="ghost"
        size="sm"
        className="text-gray-400 hover:text-white relative"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-xs flex items-center justify-center text-white font-medium">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </Button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
            <h3 className="font-semibold text-white">Notifications</h3>
            {unreadCount > 0 && (
              <button
                onClick={() => markAllAsReadMutation.mutate()}
                className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1"
                disabled={markAllAsReadMutation.isPending}
              >
                {markAllAsReadMutation.isPending ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Check className="w-3 h-3" />
                )}
                Mark all read
              </button>
            )}
          </div>

          {/* Notifications List */}
          <div className="max-h-96 overflow-y-auto">
            {isLoading ? (
              <div className="p-8 text-center">
                <Loader2 className="w-6 h-6 animate-spin text-slate-400 mx-auto" />
              </div>
            ) : notifications.length === 0 ? (
              <div className="p-8 text-center">
                <Bell className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-slate-400 text-sm">No notifications yet</p>
              </div>
            ) : (
              notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={cn(
                    "flex gap-3 px-4 py-3 hover:bg-slate-700/50 transition cursor-pointer border-b border-slate-700/50 last:border-0",
                    !notification.is_read && "bg-slate-700/30"
                  )}
                  onClick={() => {
                    if (!notification.is_read) {
                      markAsReadMutation.mutate(notification.id)
                    }
                    if (notification.action_url) {
                      setIsOpen(false)
                      window.location.href = notification.action_url
                    }
                  }}
                >
                  <div className={cn(
                    "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
                    notification.type === 'verification' && "bg-green-500/20",
                    notification.type === 'license' && "bg-blue-500/20",
                    notification.type === 'alert' && "bg-yellow-500/20",
                    notification.type === 'system' && "bg-purple-500/20",
                    notification.type === 'training' && "bg-cyan-500/20",
                  )}>
                    <NotificationIcon
                      type={notification.type}
                      isAnimated={notification.type === 'training' && notification.training_status === 'PROCESSING'}
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <p className={cn(
                        "text-sm truncate",
                        notification.is_read ? "text-slate-300" : "text-white font-medium"
                      )}>
                        {notification.title}
                      </p>
                      {!notification.is_read && (
                        <span className="w-2 h-2 bg-purple-500 rounded-full flex-shrink-0 mt-1.5" />
                      )}
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">
                      {notification.message}
                    </p>
                    {/* Training progress bar for training notifications */}
                    {notification.type === 'training' &&
                     notification.training_progress !== undefined &&
                     notification.training_status !== 'COMPLETED' &&
                     notification.training_status !== 'FAILED' && (
                      <TrainingProgressMini
                        progress={notification.training_progress}
                        status={notification.training_status}
                      />
                    )}
                    <p className="text-xs text-slate-500 mt-1">
                      {formatRelativeTime(notification.created_at)}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-slate-700 p-2">
            <Link
              href="/settings?tab=notifications"
              onClick={() => setIsOpen(false)}
              className="block w-full text-center text-sm text-purple-400 hover:text-purple-300 py-2 rounded hover:bg-slate-700/50 transition"
            >
              Notification Settings
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const router = useRouter()

  const handleLogout = () => {
    localStorage.removeItem('token')
    // Clear cookies
    document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'
    document.cookie = 'refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'
    router.push('/')
  }

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'My Identity', href: '/identity/register', icon: User },
    { name: 'Marketplace', href: '/marketplace', icon: Store },
    { name: 'Actor Packs', href: '/dashboard/packs', icon: Package },
    { name: 'Settings', href: '/settings', icon: Settings },
  ]

  return (
    <div className="min-h-screen bg-gray-900 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-800/50 border-r border-gray-700 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-gray-700">
          <Logo variant="full" size="md" href="/dashboard" />
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {navigation.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition ${
                  isActive
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                }`}
              >
                <item.icon className="w-5 h-5" />
                <span>{item.name}</span>
              </Link>
            )
          })}
        </nav>

        {/* User Section */}
        <div className="p-4 border-t border-gray-700">
          <div className="flex items-center space-x-3 px-4 py-3">
            <div className="w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center text-white font-medium">
              TU
            </div>
            <div className="flex-1">
              <p className="text-white text-sm font-medium">Test User</p>
              <p className="text-gray-400 text-xs">Pro Plan</p>
            </div>
            <ChevronDown className="w-4 h-4 text-gray-400" />
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center space-x-3 px-4 py-3 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition mt-2"
          >
            <LogOut className="w-5 h-5" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <header className="h-16 border-b border-gray-700 flex items-center justify-between px-6">
          <div className="flex items-center space-x-4">
            <h2 className="text-lg font-semibold text-white">
              {navigation.find(item => item.href === pathname)?.name || 'Dashboard'}
            </h2>
          </div>
          <div className="flex items-center space-x-4">
            <NotificationsDropdown />
            <Link href="/developers">
              <Button variant="outline" size="sm" className="border-gray-700 text-gray-300">
                API Docs
              </Button>
            </Link>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  )
}

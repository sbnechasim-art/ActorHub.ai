'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import {
  DollarSign,
  CreditCard,
  Building2,
  Mail,
  CheckCircle,
  AlertCircle,
  Clock,
  XCircle,
  Loader2,
  ArrowLeft,
  Save,
  RefreshCw,
  Info,
  ExternalLink,
  Zap,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { payoutsApi, analyticsApi, connectApi, Payout, ConnectStatus } from '@/lib/api'
import { cn, formatCurrency, formatDate } from '@/lib/utils'

type PayoutMethod = 'paypal' | 'wire'

interface PayoutSettings {
  method: PayoutMethod
  paypal_email?: string
  bank_name?: string
  bank_account_number?: string
  bank_routing_number?: string
  bank_swift_code?: string
  bank_account_holder?: string
}

const PAYOUT_STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof Clock }> = {
  PENDING: {
    label: 'Pending',
    color: 'text-yellow-500 bg-yellow-500/10',
    icon: Clock,
  },
  PROCESSING: {
    label: 'Processing',
    color: 'text-blue-500 bg-blue-500/10',
    icon: Loader2,
  },
  COMPLETED: {
    label: 'Completed',
    color: 'text-green-500 bg-green-500/10',
    icon: CheckCircle,
  },
  FAILED: {
    label: 'Failed',
    color: 'text-red-500 bg-red-500/10',
    icon: XCircle,
  },
}

const MINIMUM_PAYOUT_THRESHOLD = 50 // $50 minimum

export default function PayoutSettingsPage() {
  const queryClient = useQueryClient()

  // Notification state
  const [notification, setNotification] = useState<{
    type: 'success' | 'error'
    message: string
  } | null>(null)

  // Form state
  const [settings, setSettings] = useState<PayoutSettings>({
    method: 'paypal',
    paypal_email: '',
    bank_name: '',
    bank_account_number: '',
    bank_routing_number: '',
    bank_swift_code: '',
    bank_account_holder: '',
  })

  // Fetch current settings
  const {
    data: currentSettings,
    isLoading: isLoadingSettings,
  } = useQuery({
    queryKey: ['payout-settings'],
    queryFn: () => payoutsApi.getSettings(),
  })

  // Fetch payout history
  const {
    data: historyData,
    isLoading: isLoadingHistory,
  } = useQuery({
    queryKey: ['payout-history'],
    queryFn: () => payoutsApi.getHistory({ limit: 10 }),
  })

  // Fetch balance from analytics
  const { data: analyticsData } = useQuery({
    queryKey: ['analytics-dashboard', 30],
    queryFn: () => analyticsApi.getDashboard(30),
  })

  // Fetch Stripe Connect status
  const {
    data: connectStatus,
    isLoading: isLoadingConnect,
    refetch: refetchConnect,
  } = useQuery({
    queryKey: ['connect-status'],
    queryFn: () => connectApi.getStatus(),
  })

  // Start Connect onboarding mutation
  const startOnboardingMutation = useMutation({
    mutationFn: () => connectApi.startOnboarding(),
    onSuccess: (data) => {
      if (data.url) {
        window.location.href = data.url
      }
      queryClient.invalidateQueries({ queryKey: ['connect-status'] })
    },
    onError: (error: any) => {
      setNotification({
        type: 'error',
        message: error.response?.data?.detail || 'Failed to start onboarding',
      })
    },
  })

  // Get Connect dashboard link mutation
  const getDashboardMutation = useMutation({
    mutationFn: () => connectApi.getDashboardLink(),
    onSuccess: (data) => {
      if (data.url) {
        window.open(data.url, '_blank')
      }
    },
    onError: (error: any) => {
      setNotification({
        type: 'error',
        message: error.response?.data?.detail || 'Failed to get dashboard link',
      })
    },
  })

  const availableBalance = analyticsData?.revenue?.net_earnings || 0
  const canRequestPayout = availableBalance >= MINIMUM_PAYOUT_THRESHOLD && connectStatus?.payouts_enabled

  // Populate form when settings load
  useEffect(() => {
    if (currentSettings) {
      setSettings({
        method: currentSettings.method || 'paypal',
        paypal_email: currentSettings.paypal_email || '',
        bank_name: currentSettings.bank_name || '',
        bank_account_number: currentSettings.bank_account_number || '',
        bank_routing_number: currentSettings.bank_routing_number || '',
        bank_swift_code: currentSettings.bank_swift_code || '',
        bank_account_holder: currentSettings.bank_account_holder || '',
      })
    }
  }, [currentSettings])

  // Auto-hide notification
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [notification])

  // Update settings mutation
  const updateSettingsMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => payoutsApi.updateSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payout-settings'] })
      setNotification({
        type: 'success',
        message: 'Payout settings saved successfully!',
      })
    },
    onError: (error: any) => {
      setNotification({
        type: 'error',
        message: error.response?.data?.detail || 'Failed to save settings',
      })
    },
  })

  // Request payout mutation
  const requestPayoutMutation = useMutation({
    mutationFn: () => payoutsApi.requestPayout(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payout-history'] })
      queryClient.invalidateQueries({ queryKey: ['analytics-dashboard'] })
      setNotification({
        type: 'success',
        message: 'Payout request submitted successfully!',
      })
    },
    onError: (error: any) => {
      setNotification({
        type: 'error',
        message: error.response?.data?.detail || 'Failed to request payout',
      })
    },
  })

  // Handle form submission
  const handleSaveSettings = () => {
    const payload: Record<string, unknown> = {
      method: settings.method,
    }

    if (settings.method === 'paypal') {
      if (!settings.paypal_email) {
        setNotification({ type: 'error', message: 'PayPal email is required' })
        return
      }
      payload.paypal_email = settings.paypal_email
    } else {
      if (!settings.bank_account_holder || !settings.bank_account_number || !settings.bank_routing_number) {
        setNotification({ type: 'error', message: 'Bank details are required' })
        return
      }
      payload.bank_name = settings.bank_name
      payload.bank_account_holder = settings.bank_account_holder
      payload.bank_account_number = settings.bank_account_number
      payload.bank_routing_number = settings.bank_routing_number
      payload.bank_swift_code = settings.bank_swift_code
    }

    updateSettingsMutation.mutate(payload)
  }

  const payoutHistory = historyData?.payouts || []

  // Loading state
  if (isLoadingSettings) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-slate-800 rounded animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 h-96 bg-slate-800/50 rounded-xl animate-pulse" />
          <div className="h-64 bg-slate-800/50 rounded-xl animate-pulse" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Notification */}
      {notification && (
        <div
          className={cn(
            'fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg flex items-center gap-3 animate-in slide-in-from-top-2',
            notification.type === 'success'
              ? 'bg-green-500 text-white'
              : 'bg-red-500 text-white'
          )}
        >
          {notification.type === 'success' ? (
            <CheckCircle className="w-5 h-5" />
          ) : (
            <AlertCircle className="w-5 h-5" />
          )}
          <span>{notification.message}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Payout Settings</h1>
          <p className="text-slate-400">Configure how you receive your earnings</p>
        </div>
        <Button variant="outline" asChild>
          <Link href="/settings">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Settings
          </Link>
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Payout Settings Form */}
        <div className="lg:col-span-2 space-y-6">
          {/* Stripe Connect Card */}
          <Card className={cn(
            'border-2',
            connectStatus?.payouts_enabled
              ? 'bg-green-500/10 border-green-500/30'
              : 'bg-slate-800/50 border-slate-700'
          )}>
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div className={cn(
                    'w-12 h-12 rounded-lg flex items-center justify-center',
                    connectStatus?.payouts_enabled
                      ? 'bg-green-500/20'
                      : 'bg-purple-500/20'
                  )}>
                    {connectStatus?.payouts_enabled ? (
                      <CheckCircle className="w-6 h-6 text-green-400" />
                    ) : (
                      <CreditCard className="w-6 h-6 text-purple-400" />
                    )}
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-1">
                      {connectStatus?.payouts_enabled
                        ? 'Stripe Connected'
                        : 'Connect Stripe Account'}
                    </h3>
                    <p className="text-slate-400 text-sm max-w-md">
                      {connectStatus?.payouts_enabled
                        ? 'Your Stripe account is connected and ready to receive payouts.'
                        : 'Connect your Stripe account to receive instant payouts directly to your bank account or debit card.'}
                    </p>
                    {connectStatus?.connected && !connectStatus?.payouts_enabled && (
                      <div className="mt-2 p-2 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                        <p className="text-yellow-400 text-xs flex items-center gap-1">
                          <AlertCircle className="w-3 h-3" />
                          Complete your account setup to enable payouts
                          {connectStatus.requirements && connectStatus.requirements.length > 0 && (
                            <span> ({connectStatus.requirements.length} items remaining)</span>
                          )}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex gap-2">
                  {connectStatus?.payouts_enabled ? (
                    <Button
                      variant="outline"
                      onClick={() => getDashboardMutation.mutate()}
                      disabled={getDashboardMutation.isPending}
                    >
                      {getDashboardMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <>
                          <ExternalLink className="w-4 h-4 mr-2" />
                          View Dashboard
                        </>
                      )}
                    </Button>
                  ) : (
                    <Button
                      variant="gradient"
                      onClick={() => startOnboardingMutation.mutate()}
                      disabled={startOnboardingMutation.isPending}
                    >
                      {startOnboardingMutation.isPending ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Setting up...
                        </>
                      ) : (
                        <>
                          <Zap className="w-4 h-4 mr-2" />
                          {connectStatus?.connected ? 'Continue Setup' : 'Connect Stripe'}
                        </>
                      )}
                    </Button>
                  )}
                </div>
              </div>
              {/* Benefits list for non-connected users */}
              {!connectStatus?.payouts_enabled && (
                <div className="mt-4 pt-4 border-t border-slate-700 grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <Zap className="w-5 h-5 text-purple-400 mx-auto mb-1" />
                    <p className="text-xs text-slate-400">Instant payouts</p>
                  </div>
                  <div className="text-center">
                    <CreditCard className="w-5 h-5 text-purple-400 mx-auto mb-1" />
                    <p className="text-xs text-slate-400">Direct deposits</p>
                  </div>
                  <div className="text-center">
                    <DollarSign className="w-5 h-5 text-purple-400 mx-auto mb-1" />
                    <p className="text-xs text-slate-400">Low fees</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Balance Card */}
          <Card className="bg-gradient-to-br from-blue-600 to-purple-600 border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-blue-100 text-sm">Available Balance</p>
                  <p className="text-4xl font-bold text-white mt-1">
                    {formatCurrency(availableBalance)}
                  </p>
                  <p className="text-blue-100 text-sm mt-2">
                    Minimum payout: {formatCurrency(MINIMUM_PAYOUT_THRESHOLD)}
                  </p>
                </div>
                <Button
                  onClick={() => requestPayoutMutation.mutate()}
                  disabled={!canRequestPayout || requestPayoutMutation.isPending}
                  variant="secondary"
                  size="lg"
                >
                  {requestPayoutMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Requesting...
                    </>
                  ) : (
                    <>
                      <DollarSign className="w-4 h-4 mr-2" />
                      Request Payout
                    </>
                  )}
                </Button>
              </div>
              {!canRequestPayout && availableBalance > 0 && (
                <div className="mt-4 p-3 bg-white/10 rounded-lg flex items-start gap-2">
                  <Info className="w-4 h-4 text-blue-100 mt-0.5" />
                  <p className="text-sm text-blue-100">
                    You need at least {formatCurrency(MINIMUM_PAYOUT_THRESHOLD)} to request a payout.
                    You're {formatCurrency(MINIMUM_PAYOUT_THRESHOLD - availableBalance)} away.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Payment Method Selection */}
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Payment Method</CardTitle>
              <CardDescription>Choose how you want to receive your earnings</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Method Selection */}
              <div className="grid grid-cols-2 gap-4">
                <button
                  type="button"
                  onClick={() => setSettings({ ...settings, method: 'paypal' })}
                  className={cn(
                    'relative p-4 rounded-xl border-2 transition-all text-left',
                    settings.method === 'paypal'
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-slate-700 hover:border-slate-600'
                  )}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                      <Mail className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                      <p className="font-medium text-white">PayPal</p>
                      <p className="text-xs text-slate-400">Fast & Easy</p>
                    </div>
                  </div>
                  {settings.method === 'paypal' && (
                    <CheckCircle className="w-5 h-5 text-blue-500 absolute top-4 right-4" />
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => setSettings({ ...settings, method: 'wire' })}
                  className={cn(
                    'relative p-4 rounded-xl border-2 transition-all text-left',
                    settings.method === 'wire'
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-slate-700 hover:border-slate-600'
                  )}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                      <Building2 className="w-5 h-5 text-green-400" />
                    </div>
                    <div>
                      <p className="font-medium text-white">Bank Transfer</p>
                      <p className="text-xs text-slate-400">Direct to Bank</p>
                    </div>
                  </div>
                  {settings.method === 'wire' && (
                    <CheckCircle className="w-5 h-5 text-blue-500 absolute top-4 right-4" />
                  )}
                </button>
              </div>

              {/* PayPal Form */}
              {settings.method === 'paypal' && (
                <div className="space-y-4 pt-4 border-t border-slate-700">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      PayPal Email <span className="text-red-500">*</span>
                    </label>
                    <Input
                      type="email"
                      value={settings.paypal_email}
                      onChange={(e) => setSettings({ ...settings, paypal_email: e.target.value })}
                      placeholder="your@email.com"
                      className="bg-slate-900 border-slate-700"
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      Payouts will be sent to this PayPal account
                    </p>
                  </div>
                </div>
              )}

              {/* Wire Transfer Form */}
              {settings.method === 'wire' && (
                <div className="space-y-4 pt-4 border-t border-slate-700">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Account Holder Name <span className="text-red-500">*</span>
                      </label>
                      <Input
                        value={settings.bank_account_holder}
                        onChange={(e) =>
                          setSettings({ ...settings, bank_account_holder: e.target.value })
                        }
                        placeholder="John Doe"
                        className="bg-slate-900 border-slate-700"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Bank Name
                      </label>
                      <Input
                        value={settings.bank_name}
                        onChange={(e) => setSettings({ ...settings, bank_name: e.target.value })}
                        placeholder="Bank of America"
                        className="bg-slate-900 border-slate-700"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Account Number <span className="text-red-500">*</span>
                      </label>
                      <Input
                        value={settings.bank_account_number}
                        onChange={(e) =>
                          setSettings({ ...settings, bank_account_number: e.target.value })
                        }
                        placeholder="****1234"
                        className="bg-slate-900 border-slate-700"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        Routing Number <span className="text-red-500">*</span>
                      </label>
                      <Input
                        value={settings.bank_routing_number}
                        onChange={(e) =>
                          setSettings({ ...settings, bank_routing_number: e.target.value })
                        }
                        placeholder="021000021"
                        className="bg-slate-900 border-slate-700"
                      />
                    </div>
                    <div className="md:col-span-2">
                      <label className="block text-sm font-medium text-slate-300 mb-2">
                        SWIFT Code (International)
                      </label>
                      <Input
                        value={settings.bank_swift_code}
                        onChange={(e) =>
                          setSettings({ ...settings, bank_swift_code: e.target.value })
                        }
                        placeholder="BOFAUS3N"
                        className="bg-slate-900 border-slate-700"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Save Button */}
              <div className="flex justify-end pt-4">
                <Button
                  onClick={handleSaveSettings}
                  disabled={updateSettingsMutation.isPending}
                  variant="gradient"
                >
                  {updateSettingsMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4 mr-2" />
                      Save Settings
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Payout History */}
        <div className="space-y-6">
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-lg">Payout History</CardTitle>
              <CardDescription>Your recent payouts</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoadingHistory ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-16 bg-slate-700/50 rounded animate-pulse" />
                  ))}
                </div>
              ) : payoutHistory.length === 0 ? (
                <div className="text-center py-8">
                  <DollarSign className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                  <p className="text-slate-400 text-sm">No payouts yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {payoutHistory.map((payout: Payout) => {
                    const statusConfig =
                      PAYOUT_STATUS_CONFIG[payout.status] || PAYOUT_STATUS_CONFIG.PENDING
                    const StatusIcon = statusConfig.icon

                    return (
                      <div
                        key={payout.id}
                        className="p-3 rounded-lg bg-slate-900/50 flex items-center justify-between"
                      >
                        <div className="flex items-center gap-3">
                          <div className={cn('p-2 rounded-lg', statusConfig.color.split(' ')[1])}>
                            <StatusIcon
                              className={cn(
                                'w-4 h-4',
                                statusConfig.color.split(' ')[0],
                                payout.status === 'PROCESSING' && 'animate-spin'
                              )}
                            />
                          </div>
                          <div>
                            <p className="font-medium text-white text-sm">
                              {formatCurrency(payout.amount, payout.currency)}
                            </p>
                            <p className="text-xs text-slate-500">
                              {formatDate(payout.created_at)}
                            </p>
                          </div>
                        </div>
                        <span
                          className={cn(
                            'px-2 py-1 rounded-full text-xs font-medium',
                            statusConfig.color
                          )}
                        >
                          {statusConfig.label}
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Info Card */}
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 text-blue-400 mt-0.5" />
                <div className="text-sm text-slate-400">
                  <p className="font-medium text-slate-300 mb-1">Payout Information</p>
                  <ul className="space-y-1 text-xs">
                    <li>Payouts are processed within 3-5 business days</li>
                    <li>Minimum payout amount is {formatCurrency(MINIMUM_PAYOUT_THRESHOLD)}</li>
                    <li>PayPal payouts may incur a small fee</li>
                    <li>Wire transfers may take longer for international banks</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

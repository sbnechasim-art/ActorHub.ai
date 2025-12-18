'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Users, Shield, AlertTriangle, DollarSign, Activity,
  Eye, Ban, CheckCircle, Search, Webhook, CreditCard,
  Filter, MoreHorizontal, RefreshCw, ChevronLeft, ChevronRight,
  Clock, XCircle, Loader2, ExternalLink
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { adminApi, AdminUser, WebhookEvent, AdminPayout } from '@/lib/api'

function StatCard({ title, value, icon: Icon, trend, color, loading }: {
  title: string
  value: string | number
  icon: React.ElementType
  trend?: number
  color: string
  loading?: boolean
}) {
  return (
    <Card className="bg-slate-800/50 border-slate-700">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-400">{title}</p>
            {loading ? (
              <Loader2 className="w-6 h-6 animate-spin text-slate-400 mt-2" />
            ) : (
              <>
                <p className="text-2xl font-bold text-white mt-1">{value}</p>
                {trend !== undefined && (
                  <p className={`text-xs mt-1 ${trend > 0 ? 'text-green-400' : trend < 0 ? 'text-red-400' : 'text-slate-400'}`}>
                    {trend > 0 ? '+' : ''}{trend}% vs last month
                  </p>
                )}
              </>
            )}
          </div>
          <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${color}`}>
            <Icon className="w-6 h-6" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    active: 'bg-green-500/20 text-green-400',
    pending: 'bg-yellow-500/20 text-yellow-400',
    completed: 'bg-green-500/20 text-green-400',
    failed: 'bg-red-500/20 text-red-400',
    processing: 'bg-blue-500/20 text-blue-400',
  }
  return (
    <span className={`px-2 py-1 text-xs rounded-full capitalize ${styles[status.toLowerCase()] || 'bg-slate-500/20 text-slate-400'}`}>
      {status}
    </span>
  )
}

export default function AdminDashboard() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'payouts' | 'webhooks' | 'audit'>('overview')
  const [userSearch, setUserSearch] = useState('')
  const [userPage, setUserPage] = useState(0)
  const [webhookPage, setWebhookPage] = useState(0)

  // Dashboard stats
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['admin-dashboard'],
    queryFn: adminApi.getDashboard,
    retry: 1,
  })

  // Users
  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: ['admin-users', userSearch, userPage],
    queryFn: () => adminApi.getUsers({ search: userSearch || undefined, limit: 20, offset: userPage * 20 }),
    enabled: activeTab === 'users' || activeTab === 'overview',
  })

  // Webhooks
  const { data: webhooksData, isLoading: webhooksLoading } = useQuery({
    queryKey: ['admin-webhooks', webhookPage],
    queryFn: () => adminApi.getWebhooks({ limit: 20, offset: webhookPage * 20 }),
    enabled: activeTab === 'webhooks',
  })

  // Pending Payouts
  const { data: payoutsData, isLoading: payoutsLoading } = useQuery({
    queryKey: ['admin-payouts'],
    queryFn: adminApi.getPendingPayouts,
    enabled: activeTab === 'payouts' || activeTab === 'overview',
  })

  // Audit Logs
  const { data: auditData, isLoading: auditLoading } = useQuery({
    queryKey: ['admin-audit'],
    queryFn: () => adminApi.getAuditLogs({ limit: 50 }),
    enabled: activeTab === 'audit',
  })

  // Mutations
  const approvePayoutMutation = useMutation({
    mutationFn: adminApi.approvePayout,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-payouts'] })
      queryClient.invalidateQueries({ queryKey: ['admin-dashboard'] })
    },
  })

  const retryWebhookMutation = useMutation({
    mutationFn: adminApi.retryWebhook,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-webhooks'] })
    },
  })

  const updateUserMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { role?: string; tier?: string; is_active?: boolean } }) =>
      adminApi.updateUser(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })

  const hasApiError = statsError !== null

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/50">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-white">ActorHub Admin</h1>
              <p className="text-xs text-slate-500">Management Dashboard</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {hasApiError && (
              <span className="px-3 py-1 text-xs font-medium bg-red-500/20 text-red-400 rounded-full border border-red-500/30">
                API ERROR
              </span>
            )}
            <Button
              variant="outline"
              size="sm"
              className="border-slate-700"
              onClick={() => queryClient.invalidateQueries()}
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-64 border-r border-slate-800 min-h-[calc(100vh-64px)] p-4">
          <nav className="space-y-2">
            {[
              { id: 'overview', label: 'Overview', icon: Activity },
              { id: 'users', label: 'Users', icon: Users },
              { id: 'payouts', label: 'Payouts', icon: CreditCard, badge: payoutsData?.payouts?.length },
              { id: 'webhooks', label: 'Webhooks', icon: Webhook },
              { id: 'audit', label: 'Audit Logs', icon: Eye },
            ].map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id as typeof activeTab)}
                className={`w-full flex items-center justify-between px-4 py-3 rounded-lg transition-colors ${
                  activeTab === item.id
                    ? 'bg-purple-600 text-white'
                    : 'text-slate-400 hover:bg-slate-800'
                }`}
              >
                <div className="flex items-center gap-3">
                  <item.icon className="w-5 h-5" />
                  {item.label}
                </div>
                {item.badge ? (
                  <span className="px-2 py-0.5 text-xs bg-red-500 text-white rounded-full">
                    {item.badge}
                  </span>
                ) : null}
              </button>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <>
              {/* Stats Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <StatCard
                  title="Total Users"
                  value={stats?.total_users?.toLocaleString() || '0'}
                  icon={Users}
                  color="bg-blue-500/20 text-blue-400"
                  loading={statsLoading}
                />
                <StatCard
                  title="Active Users (30d)"
                  value={stats?.active_users?.toLocaleString() || '0'}
                  icon={Activity}
                  color="bg-green-500/20 text-green-400"
                  loading={statsLoading}
                />
                <StatCard
                  title="Revenue This Month"
                  value={`$${stats?.revenue_this_month?.toLocaleString() || '0'}`}
                  icon={DollarSign}
                  color="bg-purple-500/20 text-purple-400"
                  loading={statsLoading}
                />
                <StatCard
                  title="Pending Payouts"
                  value={payoutsData?.payouts?.length || 0}
                  icon={CreditCard}
                  color="bg-yellow-500/20 text-yellow-400"
                  loading={payoutsLoading}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <StatCard
                  title="Total Identities"
                  value={stats?.total_identities?.toLocaleString() || '0'}
                  icon={Shield}
                  color="bg-indigo-500/20 text-indigo-400"
                  loading={statsLoading}
                />
                <StatCard
                  title="Actor Packs"
                  value={stats?.total_actor_packs?.toLocaleString() || '0'}
                  icon={Eye}
                  color="bg-pink-500/20 text-pink-400"
                  loading={statsLoading}
                />
                <StatCard
                  title="API Calls Today"
                  value={stats?.api_calls_today?.toLocaleString() || '0'}
                  icon={Webhook}
                  color="bg-cyan-500/20 text-cyan-400"
                  loading={statsLoading}
                />
                <StatCard
                  title="Active Subscriptions"
                  value={stats?.active_subscriptions?.toLocaleString() || '0'}
                  icon={CheckCircle}
                  color="bg-emerald-500/20 text-emerald-400"
                  loading={statsLoading}
                />
              </div>

              {/* Quick Actions */}
              <div className="grid lg:grid-cols-2 gap-6">
                {/* Recent Users */}
                <Card className="bg-slate-800/50 border-slate-700">
                  <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="text-white">Recent Users</CardTitle>
                    <Button variant="ghost" size="sm" onClick={() => setActiveTab('users')}>
                      View All
                    </Button>
                  </CardHeader>
                  <CardContent>
                    {usersLoading ? (
                      <div className="flex justify-center py-8">
                        <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {usersData?.users?.slice(0, 5).map((user: AdminUser) => (
                          <div key={user.id} className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg">
                            <div>
                              <p className="font-medium text-white">{user.display_name || user.email.split('@')[0]}</p>
                              <p className="text-sm text-slate-400">{user.email}</p>
                            </div>
                            <StatusBadge status={user.is_active ? 'active' : 'inactive'} />
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Pending Payouts */}
                <Card className="bg-slate-800/50 border-slate-700">
                  <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="text-white flex items-center gap-2">
                      <CreditCard className="w-5 h-5 text-yellow-400" />
                      Pending Payouts
                    </CardTitle>
                    <Button variant="ghost" size="sm" onClick={() => setActiveTab('payouts')}>
                      View All
                    </Button>
                  </CardHeader>
                  <CardContent>
                    {payoutsLoading ? (
                      <div className="flex justify-center py-8">
                        <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                      </div>
                    ) : payoutsData?.payouts?.length === 0 ? (
                      <p className="text-slate-400 text-center py-8">No pending payouts</p>
                    ) : (
                      <div className="space-y-3">
                        {payoutsData?.payouts?.slice(0, 3).map((payout: AdminPayout) => (
                          <div key={payout.id} className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg">
                            <div>
                              <p className="font-medium text-white">{payout.user_email}</p>
                              <p className="text-sm text-slate-400">${payout.amount.toFixed(2)} {payout.currency}</p>
                            </div>
                            <Button
                              size="sm"
                              onClick={() => approvePayoutMutation.mutate(payout.id)}
                              disabled={approvePayoutMutation.isPending}
                              className="bg-green-600 hover:bg-green-700"
                            >
                              {approvePayoutMutation.isPending ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <CheckCircle className="w-4 h-4" />
                              )}
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </>
          )}

          {/* Users Tab */}
          {activeTab === 'users' && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-white">User Management</h2>
                <div className="flex gap-2">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <Input
                      placeholder="Search users..."
                      className="pl-10 bg-slate-800 border-slate-700 w-64"
                      value={userSearch}
                      onChange={(e) => {
                        setUserSearch(e.target.value)
                        setUserPage(0)
                      }}
                    />
                  </div>
                </div>
              </div>

              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-0">
                  {usersLoading ? (
                    <div className="flex justify-center py-12">
                      <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
                    </div>
                  ) : (
                    <>
                      <table className="w-full">
                        <thead className="border-b border-slate-700">
                          <tr>
                            <th className="text-left p-4 text-slate-400 font-medium">User</th>
                            <th className="text-left p-4 text-slate-400 font-medium">Role</th>
                            <th className="text-left p-4 text-slate-400 font-medium">Tier</th>
                            <th className="text-left p-4 text-slate-400 font-medium">Status</th>
                            <th className="text-left p-4 text-slate-400 font-medium">Joined</th>
                            <th className="text-right p-4 text-slate-400 font-medium">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {usersData?.users?.map((user: AdminUser) => (
                            <tr key={user.id} className="border-b border-slate-700/50 hover:bg-slate-800/30">
                              <td className="p-4">
                                <div>
                                  <p className="font-medium text-white">{user.display_name || 'N/A'}</p>
                                  <p className="text-sm text-slate-400">{user.email}</p>
                                </div>
                              </td>
                              <td className="p-4">
                                <span className={`px-2 py-1 text-xs rounded-full ${
                                  user.role === 'ADMIN' ? 'bg-red-500/20 text-red-400' :
                                  user.role === 'CREATOR' ? 'bg-purple-500/20 text-purple-400' :
                                  'bg-slate-500/20 text-slate-400'
                                }`}>
                                  {user.role}
                                </span>
                              </td>
                              <td className="p-4">
                                <span className={`px-2 py-1 text-xs rounded-full ${
                                  user.tier === 'ENTERPRISE' ? 'bg-yellow-500/20 text-yellow-400' :
                                  user.tier === 'PRO' ? 'bg-blue-500/20 text-blue-400' :
                                  'bg-slate-500/20 text-slate-400'
                                }`}>
                                  {user.tier}
                                </span>
                              </td>
                              <td className="p-4">
                                <StatusBadge status={user.is_active ? 'active' : 'inactive'} />
                              </td>
                              <td className="p-4 text-slate-400 text-sm">
                                {new Date(user.created_at).toLocaleDateString()}
                              </td>
                              <td className="p-4 text-right">
                                <div className="flex justify-end gap-2">
                                  {user.is_active ? (
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      className="text-red-400 hover:bg-red-500/20"
                                      onClick={() => updateUserMutation.mutate({ id: user.id, data: { is_active: false } })}
                                    >
                                      <Ban className="w-4 h-4" />
                                    </Button>
                                  ) : (
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      className="text-green-400 hover:bg-green-500/20"
                                      onClick={() => updateUserMutation.mutate({ id: user.id, data: { is_active: true } })}
                                    >
                                      <CheckCircle className="w-4 h-4" />
                                    </Button>
                                  )}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>

                      {/* Pagination */}
                      <div className="flex items-center justify-between p-4 border-t border-slate-700">
                        <p className="text-sm text-slate-400">
                          Showing {userPage * 20 + 1} - {Math.min((userPage + 1) * 20, usersData?.total || 0)} of {usersData?.total || 0}
                        </p>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-slate-700"
                            disabled={userPage === 0}
                            onClick={() => setUserPage(p => p - 1)}
                          >
                            <ChevronLeft className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-slate-700"
                            disabled={(userPage + 1) * 20 >= (usersData?.total || 0)}
                            onClick={() => setUserPage(p => p + 1)}
                          >
                            <ChevronRight className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {/* Payouts Tab */}
          {activeTab === 'payouts' && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-white">Payout Management</h2>
              </div>

              <Card className="bg-slate-800/50 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Pending Payouts</CardTitle>
                </CardHeader>
                <CardContent>
                  {payoutsLoading ? (
                    <div className="flex justify-center py-12">
                      <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
                    </div>
                  ) : payoutsData?.payouts?.length === 0 ? (
                    <div className="text-center py-12">
                      <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-4" />
                      <p className="text-slate-400">No pending payouts</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {payoutsData?.payouts?.map((payout: AdminPayout) => (
                        <div key={payout.id} className="flex items-center justify-between p-4 bg-slate-900/50 rounded-lg">
                          <div className="flex-1">
                            <div className="flex items-center gap-4">
                              <div>
                                <p className="font-medium text-white">{payout.user_email}</p>
                                <p className="text-sm text-slate-400">
                                  {payout.transaction_count} transactions • {payout.method}
                                </p>
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-6">
                            <div className="text-right">
                              <p className="text-xl font-bold text-white">
                                ${payout.amount.toFixed(2)}
                              </p>
                              <p className="text-sm text-slate-400">{payout.currency}</p>
                            </div>
                            <div className="text-right">
                              <p className="text-sm text-slate-400">Requested</p>
                              <p className="text-sm text-white">
                                {new Date(payout.requested_at).toLocaleDateString()}
                              </p>
                            </div>
                            <Button
                              onClick={() => approvePayoutMutation.mutate(payout.id)}
                              disabled={approvePayoutMutation.isPending}
                              className="bg-green-600 hover:bg-green-700"
                            >
                              {approvePayoutMutation.isPending ? (
                                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                              ) : (
                                <CheckCircle className="w-4 h-4 mr-2" />
                              )}
                              Approve
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {/* Webhooks Tab */}
          {activeTab === 'webhooks' && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-white">Webhook Events</h2>
              </div>

              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-0">
                  {webhooksLoading ? (
                    <div className="flex justify-center py-12">
                      <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
                    </div>
                  ) : (
                    <>
                      <table className="w-full">
                        <thead className="border-b border-slate-700">
                          <tr>
                            <th className="text-left p-4 text-slate-400 font-medium">Source</th>
                            <th className="text-left p-4 text-slate-400 font-medium">Event Type</th>
                            <th className="text-left p-4 text-slate-400 font-medium">Status</th>
                            <th className="text-left p-4 text-slate-400 font-medium">Attempts</th>
                            <th className="text-left p-4 text-slate-400 font-medium">Time</th>
                            <th className="text-right p-4 text-slate-400 font-medium">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {webhooksData?.events?.map((event: WebhookEvent) => (
                            <tr key={event.id} className="border-b border-slate-700/50 hover:bg-slate-800/30">
                              <td className="p-4">
                                <span className={`px-2 py-1 text-xs rounded-full ${
                                  event.source === 'STRIPE' ? 'bg-purple-500/20 text-purple-400' :
                                  event.source === 'CLERK' ? 'bg-blue-500/20 text-blue-400' :
                                  'bg-orange-500/20 text-orange-400'
                                }`}>
                                  {event.source}
                                </span>
                              </td>
                              <td className="p-4">
                                <p className="text-white font-mono text-sm">{event.event_type}</p>
                                {event.error_message && (
                                  <p className="text-xs text-red-400 mt-1">{event.error_message}</p>
                                )}
                              </td>
                              <td className="p-4">
                                <StatusBadge status={event.status} />
                              </td>
                              <td className="p-4 text-slate-400">{event.attempts}</td>
                              <td className="p-4 text-slate-400 text-sm">
                                {new Date(event.created_at).toLocaleString()}
                              </td>
                              <td className="p-4 text-right">
                                {event.status === 'FAILED' && (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="border-slate-700"
                                    onClick={() => retryWebhookMutation.mutate(event.id)}
                                    disabled={retryWebhookMutation.isPending}
                                  >
                                    {retryWebhookMutation.isPending ? (
                                      <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                      <RefreshCw className="w-4 h-4" />
                                    )}
                                  </Button>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>

                      {/* Pagination */}
                      <div className="flex items-center justify-between p-4 border-t border-slate-700">
                        <p className="text-sm text-slate-400">
                          Showing {webhookPage * 20 + 1} - {Math.min((webhookPage + 1) * 20, webhooksData?.total || 0)} of {webhooksData?.total || 0}
                        </p>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-slate-700"
                            disabled={webhookPage === 0}
                            onClick={() => setWebhookPage(p => p - 1)}
                          >
                            <ChevronLeft className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-slate-700"
                            disabled={(webhookPage + 1) * 20 >= (webhooksData?.total || 0)}
                            onClick={() => setWebhookPage(p => p + 1)}
                          >
                            <ChevronRight className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {/* Audit Logs Tab */}
          {activeTab === 'audit' && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-white">Audit Logs</h2>
              </div>

              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-0">
                  {auditLoading ? (
                    <div className="flex justify-center py-12">
                      <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
                    </div>
                  ) : (
                    <table className="w-full">
                      <thead className="border-b border-slate-700">
                        <tr>
                          <th className="text-left p-4 text-slate-400 font-medium">User</th>
                          <th className="text-left p-4 text-slate-400 font-medium">Action</th>
                          <th className="text-left p-4 text-slate-400 font-medium">Resource</th>
                          <th className="text-left p-4 text-slate-400 font-medium">Status</th>
                          <th className="text-left p-4 text-slate-400 font-medium">IP</th>
                          <th className="text-left p-4 text-slate-400 font-medium">Time</th>
                        </tr>
                      </thead>
                      <tbody>
                        {auditData?.logs?.map((log) => (
                          <tr key={log.id} className="border-b border-slate-700/50 hover:bg-slate-800/30">
                            <td className="p-4 text-white">{log.user_email || 'System'}</td>
                            <td className="p-4">
                              <span className="px-2 py-1 text-xs bg-slate-700 text-slate-300 rounded font-mono">
                                {log.action}
                              </span>
                            </td>
                            <td className="p-4 text-slate-400">{log.resource_type}</td>
                            <td className="p-4">
                              {log.success ? (
                                <CheckCircle className="w-4 h-4 text-green-400" />
                              ) : (
                                <XCircle className="w-4 h-4 text-red-400" />
                              )}
                            </td>
                            <td className="p-4 text-slate-400 font-mono text-sm">{log.ip_address || '-'}</td>
                            <td className="p-4 text-slate-400 text-sm">
                              {new Date(log.created_at).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

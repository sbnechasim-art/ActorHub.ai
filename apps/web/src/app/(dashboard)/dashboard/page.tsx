'use client'

import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Shield, DollarSign, Eye, TrendingUp, Plus, ArrowRight, LogOut } from 'lucide-react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { userApi, identityApi } from '@/lib/api'
import { useAuth } from '@/hooks/useAuth'

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value)
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('en-US').format(value)
}

function StatsCard({
  title,
  value,
  icon: Icon,
  trend,
  color = 'blue'
}: {
  title: string
  value: string | number
  icon: any
  trend?: string
  color?: 'blue' | 'green' | 'purple' | 'orange'
}) {
  const colors = {
    blue: 'bg-blue-500/20 text-blue-400',
    green: 'bg-green-500/20 text-green-400',
    purple: 'bg-purple-500/20 text-purple-400',
    orange: 'bg-orange-500/20 text-orange-400',
  }

  return (
    <Card className="bg-slate-800/50 border-slate-700">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-400">{title}</p>
            <p className="text-2xl font-bold text-white mt-1">{value}</p>
            {trend && (
              <p className="text-xs text-slate-500 mt-1">{trend}</p>
            )}
          </div>
          <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${colors[color]}`}>
            <Icon className="w-6 h-6" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function IdentityCard({ identity }: { identity: any }) {
  return (
    <Card className="bg-slate-800/50 border-slate-700 hover:border-slate-600 transition cursor-pointer">
      <CardContent className="p-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-slate-700 overflow-hidden flex items-center justify-center">
            {identity.profile_image_url ? (
              <img
                src={identity.profile_image_url}
                alt={identity.display_name}
                className="w-full h-full object-cover"
              />
            ) : (
              <Shield className="w-8 h-8 text-slate-500" />
            )}
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-white">{identity.display_name}</h3>
            <div className="flex items-center gap-2 mt-1">
              <span className={`px-2 py-0.5 rounded-full text-xs ${
                identity.status === 'verified'
                  ? 'bg-green-500/20 text-green-400'
                  : 'bg-yellow-500/20 text-yellow-400'
              }`}>
                {identity.status}
              </span>
              <span className="text-xs text-slate-500">
                {identity.protection_level}
              </span>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm text-white">{formatNumber(identity.total_verifications)}</p>
            <p className="text-xs text-slate-500">verifications</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function DashboardPage() {
  const { user, isLoading: authLoading, isAuthenticated, logout, requireAuth } = useAuth()

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      requireAuth()
    }
  }, [authLoading, isAuthenticated, requireAuth])

  // Fetch dashboard stats from real API
  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => userApi.getDashboard(),
    enabled: isAuthenticated,
  })

  // Fetch user's identities from real API
  const { data: identities, isLoading: identitiesLoading } = useQuery({
    queryKey: ['my-identities'],
    queryFn: () => identityApi.getMyIdentities(),
    enabled: isAuthenticated,
  })

  // Show loading while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-white">Loading...</div>
      </div>
    )
  }

  // Don't render if not authenticated (will redirect)
  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="p-8">
      {/* Welcome Section with Logout */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">
            Welcome back, {user?.first_name || user?.display_name || user?.email?.split('@')[0] || 'Creator'}
          </h1>
          <p className="text-slate-400 mt-2">
            Manage your protected identities and track your earnings
          </p>
        </div>
        <Button
          variant="outline"
          onClick={logout}
          className="border-slate-700 text-slate-300 hover:text-white"
        >
          <LogOut className="w-4 h-4 mr-2" />
          Logout
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatsCard
          title="Protected Identities"
          value={stats?.identities_count || 0}
          icon={Shield}
          color="blue"
        />
        <StatsCard
          title="Total Revenue"
          value={formatCurrency(stats?.total_revenue || 0)}
          icon={DollarSign}
          trend="+15% vs last month"
          color="green"
        />
        <StatsCard
          title="Verification Checks"
          value={formatNumber(stats?.verification_checks || 0)}
          icon={Eye}
          trend="This month"
          color="purple"
        />
        <StatsCard
          title="Active Licenses"
          value={stats?.active_licenses || 0}
          icon={TrendingUp}
          color="orange"
        />
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Identities List */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white">Your Identities</h2>
            <Link href="/identity/register">
              <Button className="bg-purple-600 hover:bg-purple-700">
                <Plus className="w-4 h-4 mr-2" />
                Register New
              </Button>
            </Link>
          </div>

          {identitiesLoading ? (
            <div className="space-y-4">
              {[1, 2].map((i) => (
                <Card key={i} className="bg-slate-800/50 border-slate-700">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-4">
                      <div className="w-16 h-16 rounded-full bg-slate-700 animate-pulse" />
                      <div className="flex-1 space-y-2">
                        <div className="h-4 bg-slate-700 rounded w-1/3 animate-pulse" />
                        <div className="h-3 bg-slate-700 rounded w-1/4 animate-pulse" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : identities && identities.length > 0 ? (
            <div className="space-y-4">
              {identities.map((identity: any) => (
                <Link key={identity.id} href={`/identity/${identity.id}`}>
                  <IdentityCard identity={identity} />
                </Link>
              ))}
            </div>
          ) : (
            <Card className="bg-slate-800/50 border-slate-700">
              <CardContent className="p-12 text-center">
                <Shield className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">
                  No identities yet
                </h3>
                <p className="text-slate-400 mb-6">
                  Register your first identity to start protecting your digital presence
                </p>
                <Link href="/identity/register">
                  <Button className="bg-purple-600 hover:bg-purple-700">
                    Register Identity
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                </Link>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Link href="/identity/create" className="block">
                <Button className="w-full justify-start bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white">
                  <Plus className="w-4 h-4 mr-2" />
                  Create AI Content
                </Button>
              </Link>
              <Link href="/identity/register" className="block">
                <Button variant="outline" className="w-full justify-start border-slate-700 text-slate-300">
                  <Shield className="w-4 h-4 mr-2" />
                  Register New Identity
                </Button>
              </Link>
              <Link href="/marketplace" className="block">
                <Button variant="outline" className="w-full justify-start border-slate-700 text-slate-300">
                  <DollarSign className="w-4 h-4 mr-2" />
                  Browse Marketplace
                </Button>
              </Link>
              <Link href="/settings" className="block">
                <Button variant="outline" className="w-full justify-start border-slate-700 text-slate-300">
                  <TrendingUp className="w-4 h-4 mr-2" />
                  Manage API Keys
                </Button>
              </Link>
            </CardContent>
          </Card>

          {/* Upgrade Card */}
          <Card className="bg-gradient-to-br from-blue-600/20 to-purple-600/20 border-blue-500/30">
            <CardContent className="p-6">
              <h3 className="font-semibold text-white mb-2">Upgrade to Pro</h3>
              <p className="text-sm text-slate-300 mb-4">
                Get advanced features, priority support, and higher earnings.
              </p>
              <Link href="/pricing">
                <Button className="w-full bg-purple-600 hover:bg-purple-700">
                  Upgrade Now
                </Button>
              </Link>
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
                    <Eye className="w-4 h-4 text-green-400" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-white">Identity verified</p>
                    <p className="text-xs text-slate-500">2 hours ago</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
                    <DollarSign className="w-4 h-4 text-blue-400" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-white">License purchased</p>
                    <p className="text-xs text-slate-500">5 hours ago</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center">
                    <Shield className="w-4 h-4 text-purple-400" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-white">New protection alert</p>
                    <p className="text-xs text-slate-500">1 day ago</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

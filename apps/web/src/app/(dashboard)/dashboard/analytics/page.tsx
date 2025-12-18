'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import {
  DollarSign,
  TrendingUp,
  Shield,
  FileText,
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  AlertCircle,
  RefreshCw,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { analyticsApi, AnalyticsDashboard } from '@/lib/api'
import { cn, formatCurrency, formatNumber } from '@/lib/utils'

const TIME_PERIODS = [
  { value: 7, label: '7 Days' },
  { value: 30, label: '30 Days' },
  { value: 90, label: '90 Days' },
]

export default function AnalyticsPage() {
  const [days, setDays] = useState(30)

  // Fetch analytics data
  const {
    data: analytics,
    isLoading,
    error,
    refetch,
    isRefetching,
  } = useQuery<AnalyticsDashboard>({
    queryKey: ['analytics-dashboard', days],
    queryFn: () => analyticsApi.getDashboard(days),
  })

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Header skeleton */}
        <div className="flex items-center justify-between">
          <div>
            <div className="h-8 w-48 bg-slate-800 rounded animate-pulse" />
            <div className="h-4 w-64 bg-slate-800 rounded animate-pulse mt-2" />
          </div>
          <div className="h-10 w-48 bg-slate-800 rounded animate-pulse" />
        </div>

        {/* Cards skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-slate-800/50 rounded-xl animate-pulse" />
          ))}
        </div>

        {/* Charts skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[1, 2].map((i) => (
            <div key={i} className="h-80 bg-slate-800/50 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Card className="bg-slate-800/50 border-slate-700 max-w-md">
          <CardContent className="p-8 text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Failed to Load Analytics</h2>
            <p className="text-slate-400 mb-6">
              We couldn't load your analytics data. Please try again.
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

  // Calculate trends (compare to previous period)
  const calculateTrend = (data: Array<{ date: string; value: number }>) => {
    if (!data || data.length < 2) return { value: 0, isPositive: true }
    const midpoint = Math.floor(data.length / 2)
    const firstHalf = data.slice(0, midpoint).reduce((sum, d) => sum + d.value, 0)
    const secondHalf = data.slice(midpoint).reduce((sum, d) => sum + d.value, 0)
    if (firstHalf === 0) return { value: 0, isPositive: true }
    const change = ((secondHalf - firstHalf) / firstHalf) * 100
    return { value: Math.abs(change).toFixed(1), isPositive: change >= 0 }
  }

  const usageTrend = calculateTrend(analytics?.usage_trend || [])
  const revenueTrend = calculateTrend(analytics?.revenue_trend || [])

  // Format chart data
  const formatChartDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const usageChartData = (analytics?.usage_trend || []).map((d) => ({
    date: formatChartDate(d.date),
    usage: d.value,
  }))

  const revenueChartData = (analytics?.revenue_trend || []).map((d) => ({
    date: formatChartDate(d.date),
    revenue: d.value,
  }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Analytics Dashboard</h1>
          <p className="text-slate-400">Track your performance and revenue</p>
        </div>

        {/* Time Period Selector */}
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-slate-500" />
          <div className="inline-flex rounded-lg bg-slate-800 p-1">
            {TIME_PERIODS.map((period) => (
              <button
                key={period.value}
                onClick={() => setDays(period.value)}
                className={cn(
                  'px-4 py-2 text-sm font-medium rounded-md transition-colors',
                  days === period.value
                    ? 'bg-blue-500 text-white'
                    : 'text-slate-400 hover:text-white'
                )}
              >
                {period.label}
              </button>
            ))}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => refetch()}
            disabled={isRefetching}
          >
            <RefreshCw className={cn('w-4 h-4', isRefetching && 'animate-spin')} />
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Revenue */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-lg bg-green-500/10">
                <DollarSign className="w-5 h-5 text-green-500" />
              </div>
              <div
                className={cn(
                  'flex items-center gap-1 text-sm',
                  revenueTrend.isPositive ? 'text-green-500' : 'text-red-500'
                )}
              >
                {revenueTrend.isPositive ? (
                  <ArrowUpRight className="w-4 h-4" />
                ) : (
                  <ArrowDownRight className="w-4 h-4" />
                )}
                {revenueTrend.value}%
              </div>
            </div>
            <div className="mt-4">
              <p className="text-sm text-slate-400">Total Revenue</p>
              <p className="text-2xl font-bold text-white">
                {formatCurrency(analytics?.revenue?.total_revenue || 0)}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Net Earnings */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-lg bg-blue-500/10">
                <TrendingUp className="w-5 h-5 text-blue-500" />
              </div>
            </div>
            <div className="mt-4">
              <p className="text-sm text-slate-400">Net Earnings</p>
              <p className="text-2xl font-bold text-white">
                {formatCurrency(analytics?.revenue?.net_earnings || 0)}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Total Verifications */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-lg bg-purple-500/10">
                <Shield className="w-5 h-5 text-purple-500" />
              </div>
              <div
                className={cn(
                  'flex items-center gap-1 text-sm',
                  usageTrend.isPositive ? 'text-green-500' : 'text-red-500'
                )}
              >
                {usageTrend.isPositive ? (
                  <ArrowUpRight className="w-4 h-4" />
                ) : (
                  <ArrowDownRight className="w-4 h-4" />
                )}
                {usageTrend.value}%
              </div>
            </div>
            <div className="mt-4">
              <p className="text-sm text-slate-400">Total Verifications</p>
              <p className="text-2xl font-bold text-white">
                {formatNumber(analytics?.usage?.total_verifications || 0)}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Transactions */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-lg bg-orange-500/10">
                <FileText className="w-5 h-5 text-orange-500" />
              </div>
            </div>
            <div className="mt-4">
              <p className="text-sm text-slate-400">Total Transactions</p>
              <p className="text-2xl font-bold text-white">
                {formatNumber(analytics?.revenue?.transaction_count || 0)}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Trend */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white">Revenue Trend</CardTitle>
            <CardDescription>Daily revenue over the selected period</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {revenueChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={revenueChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis
                      dataKey="date"
                      stroke="#64748b"
                      tick={{ fill: '#64748b', fontSize: 12 }}
                    />
                    <YAxis
                      stroke="#64748b"
                      tick={{ fill: '#64748b', fontSize: 12 }}
                      tickFormatter={(value) => `$${value}`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '8px',
                      }}
                      labelStyle={{ color: '#f8fafc' }}
                      formatter={(value: number) => [`$${value.toFixed(2)}`, 'Revenue']}
                    />
                    <Line
                      type="monotone"
                      dataKey="revenue"
                      stroke="#22c55e"
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4, fill: '#22c55e' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-500">
                  No revenue data for this period
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Usage Trend */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white">Usage Trend</CardTitle>
            <CardDescription>Daily API usage over the selected period</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {usageChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={usageChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis
                      dataKey="date"
                      stroke="#64748b"
                      tick={{ fill: '#64748b', fontSize: 12 }}
                    />
                    <YAxis
                      stroke="#64748b"
                      tick={{ fill: '#64748b', fontSize: 12 }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '8px',
                      }}
                      labelStyle={{ color: '#f8fafc' }}
                      formatter={(value: number) => [formatNumber(value), 'Usage']}
                    />
                    <Bar dataKey="usage" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-500">
                  No usage data for this period
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Performing Identities */}
      <Card className="bg-slate-800/50 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white">Top Performing Identities</CardTitle>
          <CardDescription>Your best performing identities by usage and revenue</CardDescription>
        </CardHeader>
        <CardContent>
          {!analytics?.top_identities || analytics.top_identities.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              No identity data available for this period
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Identity
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Verifications
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Licenses Sold
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Revenue
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {analytics.top_identities.map((identity, index) => (
                    <tr key={identity.identity_id} className="hover:bg-slate-800/50">
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div
                            className={cn(
                              'w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-sm',
                              index === 0
                                ? 'bg-gradient-to-br from-yellow-400 to-orange-500'
                                : index === 1
                                ? 'bg-gradient-to-br from-slate-300 to-slate-500'
                                : index === 2
                                ? 'bg-gradient-to-br from-orange-400 to-orange-600'
                                : 'bg-slate-700'
                            )}
                          >
                            {index + 1}
                          </div>
                          <span className="font-medium text-white">{identity.identity_name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-4 text-right text-white">
                        {formatNumber(identity.verifications)}
                      </td>
                      <td className="px-4 py-4 text-right text-white">
                        {formatNumber(identity.licenses_sold)}
                      </td>
                      <td className="px-4 py-4 text-right text-green-500 font-medium">
                        {formatCurrency(identity.revenue)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

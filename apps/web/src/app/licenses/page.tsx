'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import {
  FileText,
  Download,
  Filter,
  ExternalLink,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  Search,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { licensesApi, License } from '@/lib/api'
import { cn, formatDate, formatCurrency } from '@/lib/utils'

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof CheckCircle }> = {
  active: {
    label: 'Active',
    color: 'text-green-500 bg-green-500/10',
    icon: CheckCircle,
  },
  expired: {
    label: 'Expired',
    color: 'text-red-500 bg-red-500/10',
    icon: XCircle,
  },
  pending: {
    label: 'Pending',
    color: 'text-yellow-500 bg-yellow-500/10',
    icon: Clock,
  },
}

const LICENSE_TYPE_LABELS: Record<string, string> = {
  PERSONAL: 'Personal',
  COMMERCIAL: 'Commercial',
  ENTERPRISE: 'Enterprise',
}

const ITEMS_PER_PAGE = 10

export default function LicensesPage() {
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(1)

  // Fetch licenses
  const {
    data: licensesData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['licenses', statusFilter, page],
    queryFn: () =>
      licensesApi.getMine({
        status: statusFilter !== 'all' ? statusFilter : undefined,
        limit: ITEMS_PER_PAGE,
        offset: (page - 1) * ITEMS_PER_PAGE,
      }),
  })

  const licenses = licensesData?.licenses || []
  const total = licensesData?.total || 0
  const totalPages = Math.ceil(total / ITEMS_PER_PAGE)

  // Filter by search
  const filteredLicenses = licenses.filter((license: License) => {
    if (!searchQuery) return true
    const searchLower = searchQuery.toLowerCase()
    return (
      license.identity?.name?.toLowerCase().includes(searchLower) ||
      license.license_type.toLowerCase().includes(searchLower)
    )
  })

  // Check if license is expired
  const isExpired = (license: License) => {
    if (!license.expires_at) return false
    return new Date(license.expires_at) < new Date()
  }

  // Get license status
  const getLicenseStatus = (license: License) => {
    if (!license.is_active) return 'expired'
    if (isExpired(license)) return 'expired'
    if (license.payment_status === 'PENDING') return 'pending'
    return 'active'
  }

  // Download license PDF
  const downloadLicensePdf = (license: License) => {
    // Generate PDF download URL
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
    const downloadUrl = `${apiUrl}/marketplace/licenses/${license.id}/pdf`
    window.open(downloadUrl, '_blank')
  }

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
        <header className="border-b border-slate-800">
          <div className="container mx-auto px-4 h-16 flex items-center">
            <div className="h-6 w-32 bg-slate-800 rounded animate-pulse" />
          </div>
        </header>
        <main className="container mx-auto px-4 py-8">
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-20 bg-slate-800/50 rounded-xl animate-pulse" />
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
            <h2 className="text-xl font-semibold text-white mb-2">Failed to Load Licenses</h2>
            <p className="text-slate-400 mb-6">
              We couldn't load your licenses. Please try again later.
            </p>
            <Button variant="outline" onClick={() => window.location.reload()}>
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
          <div className="flex items-center gap-4">
            <FileText className="w-6 h-6 text-blue-500" />
            <h1 className="text-xl font-semibold text-white">My Licenses</h1>
          </div>
          <Button variant="outline" asChild>
            <Link href="/marketplace">Browse Marketplace</Link>
          </Button>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Filters & Search */}
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search licenses..."
              className="bg-slate-800 border-slate-700 pl-10"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-500" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setPage(1)
              }}
              className="h-10 rounded-md border bg-slate-800 border-slate-700 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Licenses</option>
              <option value="active">Active</option>
              <option value="expired">Expired</option>
              <option value="pending">Pending</option>
            </select>
          </div>
        </div>

        {/* Stats Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-lg bg-green-500/10">
                <CheckCircle className="w-5 h-5 text-green-500" />
              </div>
              <div>
                <p className="text-sm text-slate-400">Active Licenses</p>
                <p className="text-2xl font-bold text-white">
                  {licenses.filter((l: License) => getLicenseStatus(l) === 'active').length}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-lg bg-red-500/10">
                <XCircle className="w-5 h-5 text-red-500" />
              </div>
              <div>
                <p className="text-sm text-slate-400">Expired Licenses</p>
                <p className="text-2xl font-bold text-white">
                  {licenses.filter((l: License) => getLicenseStatus(l) === 'expired').length}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-lg bg-blue-500/10">
                <FileText className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <p className="text-sm text-slate-400">Total Licenses</p>
                <p className="text-2xl font-bold text-white">{total}</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Licenses Table */}
        {filteredLicenses.length === 0 ? (
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="p-12 text-center">
              <FileText className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">No Licenses Found</h3>
              <p className="text-slate-400 mb-6">
                {searchQuery
                  ? 'No licenses match your search criteria.'
                  : "You haven't purchased any licenses yet."}
              </p>
              <Button variant="gradient" asChild>
                <Link href="/marketplace">Browse Marketplace</Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card className="bg-slate-800/50 border-slate-700 overflow-hidden">
            {/* Desktop Table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-900/50">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Identity
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                      License Type
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Price
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Expires
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-4 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {filteredLicenses.map((license: License) => {
                    const status = getLicenseStatus(license)
                    const statusConfig = STATUS_CONFIG[status]
                    const StatusIcon = statusConfig.icon

                    return (
                      <tr key={license.id} className="hover:bg-slate-800/50 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
                              {license.identity?.name?.charAt(0) || '?'}
                            </div>
                            <div>
                              <p className="font-medium text-white">
                                {license.identity?.name || 'Unknown Identity'}
                              </p>
                              <p className="text-sm text-slate-400">
                                Purchased {formatDate(license.created_at)}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400">
                            {LICENSE_TYPE_LABELS[license.license_type] || license.license_type}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-white">
                          {formatCurrency(license.price, license.currency)}
                        </td>
                        <td className="px-6 py-4 text-slate-400">
                          {license.expires_at ? formatDate(license.expires_at) : 'Never'}
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={cn(
                              'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium',
                              statusConfig.color
                            )}
                          >
                            <StatusIcon className="w-3 h-3" />
                            {statusConfig.label}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => downloadLicensePdf(license)}
                              title="Download License PDF"
                            >
                              <Download className="w-4 h-4" />
                            </Button>
                            {license.identity && (
                              <Button variant="ghost" size="sm" asChild>
                                <Link href={`/identity/${license.identity_id}`}>
                                  <ExternalLink className="w-4 h-4" />
                                </Link>
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards */}
            <div className="md:hidden divide-y divide-slate-700">
              {filteredLicenses.map((license: License) => {
                const status = getLicenseStatus(license)
                const statusConfig = STATUS_CONFIG[status]
                const StatusIcon = statusConfig.icon

                return (
                  <div key={license.id} className="p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
                          {license.identity?.name?.charAt(0) || '?'}
                        </div>
                        <div>
                          <p className="font-medium text-white">
                            {license.identity?.name || 'Unknown'}
                          </p>
                          <span
                            className={cn(
                              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                              statusConfig.color
                            )}
                          >
                            <StatusIcon className="w-3 h-3" />
                            {statusConfig.label}
                          </span>
                        </div>
                      </div>
                      <span className="text-lg font-bold text-white">
                        {formatCurrency(license.price, license.currency)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <div className="text-slate-400">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-blue-500/10 text-blue-400">
                          {LICENSE_TYPE_LABELS[license.license_type] || license.license_type}
                        </span>
                      </div>
                      <div className="text-slate-400">
                        Expires: {license.expires_at ? formatDate(license.expires_at) : 'Never'}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() => downloadLicensePdf(license)}
                      >
                        <Download className="w-4 h-4 mr-2" />
                        Download PDF
                      </Button>
                      {license.identity && (
                        <Button variant="outline" size="sm" asChild>
                          <Link href={`/identity/${license.identity_id}`}>
                            <ExternalLink className="w-4 h-4" />
                          </Link>
                        </Button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </Card>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-6">
            <p className="text-sm text-slate-400">
              Showing {(page - 1) * ITEMS_PER_PAGE + 1} to{' '}
              {Math.min(page * ITEMS_PER_PAGE, total)} of {total} licenses
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <span className="text-sm text-slate-400">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
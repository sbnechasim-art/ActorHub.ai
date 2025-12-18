'use client'

import { useParams, useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import {
  Shield,
  Edit,
  Trash2,
  Download,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  TrendingUp,
  DollarSign,
  Eye,
  ArrowLeft,
  RefreshCw,
} from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { identityApi, analyticsApi, actorPackApi, Identity, ActorPack } from '@/lib/api'
import { useState } from 'react'

// Status configuration
const STATUS_CONFIG = {
  PENDING: {
    label: 'Pending Verification',
    color: 'text-yellow-500',
    bg: 'bg-yellow-500/10',
    icon: Clock,
    message: 'Your identity is waiting to be verified.',
  },
  VERIFIED: {
    label: 'Verified',
    color: 'text-blue-500',
    bg: 'bg-blue-500/10',
    icon: CheckCircle,
    message: 'Your identity has been verified.',
  },
  PROTECTED: {
    label: 'Protected',
    color: 'text-green-500',
    bg: 'bg-green-500/10',
    icon: Shield,
    message: 'Your identity is fully protected and active.',
  },
  SUSPENDED: {
    label: 'Suspended',
    color: 'text-red-500',
    bg: 'bg-red-500/10',
    icon: XCircle,
    message: 'Your identity has been suspended. Please contact support.',
  },
}

const TRAINING_STATUS_CONFIG = {
  PENDING: {
    label: 'Waiting to Start',
    color: 'text-gray-400',
    message: 'Training will begin shortly.',
  },
  PROCESSING: {
    label: 'Training in Progress',
    color: 'text-blue-500',
    message: 'Your Actor Pack is being trained. This may take 15-30 minutes.',
  },
  COMPLETED: {
    label: 'Training Complete',
    color: 'text-green-500',
    message: 'Your Actor Pack is ready to use.',
  },
  FAILED: {
    label: 'Training Failed',
    color: 'text-red-500',
    message: 'Training encountered an error.',
  },
}

// Skeleton components
function SkeletonCard() {
  return (
    <Card className="bg-slate-800 border-slate-700 animate-pulse">
      <CardHeader>
        <div className="h-6 bg-slate-700 rounded w-1/3" />
      </CardHeader>
      <CardContent>
        <div className="h-4 bg-slate-700 rounded w-full mb-2" />
        <div className="h-4 bg-slate-700 rounded w-2/3" />
      </CardContent>
    </Card>
  )
}

function SkeletonChart() {
  return (
    <Card className="bg-slate-800 border-slate-700 animate-pulse">
      <CardHeader>
        <div className="h-6 bg-slate-700 rounded w-1/4" />
      </CardHeader>
      <CardContent>
        <div className="h-64 bg-slate-700 rounded" />
      </CardContent>
    </Card>
  )
}

export default function IdentityDetailPage() {
  const params = useParams()
  const router = useRouter()
  const queryClient = useQueryClient()
  const identityId = params.id as string

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  // Fetch identity details
  const {
    data: identity,
    isLoading: identityLoading,
    error: identityError,
  } = useQuery({
    queryKey: ['identity', identityId],
    queryFn: () => identityApi.getIdentity(identityId),
    enabled: !!identityId,
    refetchInterval: (data) => {
      // Poll more frequently while training
      if (data?.actor_pack?.training_status === 'PROCESSING') {
        return 10000 // 10 seconds
      }
      return false
    },
  })

  // Fetch analytics for this identity
  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ['identity-analytics', identityId],
    queryFn: () => analyticsApi.getIdentityAnalytics(identityId, 30),
    enabled: !!identityId,
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => identityApi.update(identityId, { deleted_at: new Date().toISOString() }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['identities'] })
      router.push('/dashboard')
    },
  })

  // Retry training mutation
  const retryTrainingMutation = useMutation({
    mutationFn: () => {
      const formData = new FormData()
      formData.append('identity_id', identityId)
      return actorPackApi.initTraining(formData)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['identity', identityId] })
    },
  })

  if (identityLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center space-x-4 mb-6">
          <div className="h-8 w-8 bg-slate-700 rounded animate-pulse" />
          <div className="h-8 w-48 bg-slate-700 rounded animate-pulse" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <SkeletonChart />
      </div>
    )
  }

  if (identityError || !identity) {
    return (
      <div className="p-6">
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="w-16 h-16 text-red-500 mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Identity Not Found</h2>
            <p className="text-gray-400 mb-6">
              The identity you're looking for doesn't exist or you don't have access.
            </p>
            <Link href="/dashboard">
              <Button variant="outline">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  const statusConfig = STATUS_CONFIG[identity.status] || STATUS_CONFIG.PENDING
  const StatusIcon = statusConfig.icon
  const actorPack = identity.actor_pack as ActorPack | undefined
  const trainingConfig = actorPack
    ? TRAINING_STATUS_CONFIG[actorPack.training_status] || TRAINING_STATUS_CONFIG.PENDING
    : null

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link href="/dashboard">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-white">
              {identity.display_name || identity.name}
            </h1>
            <p className="text-gray-400">{identity.bio || 'No description'}</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <Link href={`/identity/${identityId}/edit`}>
            <Button variant="outline" className="border-slate-600">
              <Edit className="w-4 h-4 mr-2" />
              Edit
            </Button>
          </Link>
          <Button
            variant="destructive"
            onClick={() => setShowDeleteConfirm(true)}
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {/* Status Banner */}
      <Card className={`${statusConfig.bg} border-0`}>
        <CardContent className="flex items-center justify-between py-4">
          <div className="flex items-center space-x-3">
            <StatusIcon className={`w-6 h-6 ${statusConfig.color}`} />
            <div>
              <p className={`font-semibold ${statusConfig.color}`}>{statusConfig.label}</p>
              <p className="text-gray-400 text-sm">{statusConfig.message}</p>
            </div>
          </div>
          <div className={`px-4 py-2 rounded-full ${statusConfig.bg} ${statusConfig.color} font-medium`}>
            {identity.protection_level}
          </div>
        </CardContent>
      </Card>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Total Verifications</p>
                <p className="text-2xl font-bold text-white">
                  {analytics?.usage_by_action?.verify?.reduce(
                    (sum: number, d: { count: number }) => sum + d.count,
                    0
                  ) || identity.total_verifications || 0}
                </p>
              </div>
              <Eye className="w-8 h-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Licenses Sold</p>
                <p className="text-2xl font-bold text-white">
                  {analytics?.licenses_sold || 0}
                </p>
              </div>
              <Shield className="w-8 h-8 text-purple-500" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Total Revenue</p>
                <p className="text-2xl font-bold text-white">
                  ${(analytics?.total_revenue || identity.total_revenue || 0).toFixed(2)}
                </p>
              </div>
              <DollarSign className="w-8 h-8 text-green-500" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Quality Score</p>
                <p className="text-2xl font-bold text-white">
                  {actorPack?.quality_score?.toFixed(0) || 'N/A'}
                </p>
              </div>
              <TrendingUp className="w-8 h-8 text-yellow-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Training Status */}
      {actorPack && (
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white">Actor Pack Training</CardTitle>
            <CardDescription>
              {trainingConfig?.message}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className={trainingConfig?.color}>
                  {trainingConfig?.label}
                </span>
                <span className="text-gray-400">
                  {actorPack.training_progress}%
                </span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-3">
                <div
                  className={`h-3 rounded-full transition-all duration-500 ${
                    actorPack.training_status === 'COMPLETED'
                      ? 'bg-green-500'
                      : actorPack.training_status === 'FAILED'
                      ? 'bg-red-500'
                      : 'bg-blue-500'
                  }`}
                  style={{ width: `${actorPack.training_progress}%` }}
                />
              </div>
            </div>

            {/* Training Details */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-slate-700">
              <div>
                <p className="text-gray-400 text-sm">Authenticity</p>
                <p className="text-white font-semibold">
                  {actorPack.authenticity_score?.toFixed(0) || 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Consistency</p>
                <p className="text-white font-semibold">
                  {actorPack.consistency_score?.toFixed(0) || 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Status</p>
                <p className={`font-semibold ${trainingConfig?.color}`}>
                  {actorPack.is_available ? 'Available' : 'Not Available'}
                </p>
              </div>
            </div>

            {/* Error Message */}
            {actorPack.training_status === 'FAILED' && actorPack.training_error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mt-4">
                <div className="flex items-start space-x-3">
                  <XCircle className="w-5 h-5 text-red-500 mt-0.5" />
                  <div>
                    <p className="text-red-500 font-medium">Training Failed</p>
                    <p className="text-gray-400 text-sm mt-1">
                      {actorPack.training_error}
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-3 border-red-500 text-red-500 hover:bg-red-500/10"
                      onClick={() => retryTrainingMutation.mutate()}
                      disabled={retryTrainingMutation.isPending}
                    >
                      <RefreshCw className={`w-4 h-4 mr-2 ${retryTrainingMutation.isPending ? 'animate-spin' : ''}`} />
                      Retry Training
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Download Button */}
            {actorPack.training_status === 'COMPLETED' && actorPack.is_available && (
              <div className="pt-4">
                <Button
                  variant="gradient"
                  className="w-full"
                  onClick={() => actorPackApi.download(identityId)}
                >
                  <Download className="w-4 h-4 mr-2" />
                  Download Actor Pack
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Usage Chart */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white">Verification Activity</CardTitle>
          <CardDescription>Last 30 days</CardDescription>
        </CardHeader>
        <CardContent>
          {analyticsLoading ? (
            <div className="h-64 flex items-center justify-center">
              <RefreshCw className="w-8 h-8 text-gray-500 animate-spin" />
            </div>
          ) : analytics?.daily_usage?.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={analytics.daily_usage}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="date"
                  stroke="#94a3b8"
                  tick={{ fill: '#94a3b8', fontSize: 12 }}
                />
                <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                  }}
                  labelStyle={{ color: '#fff' }}
                />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center text-gray-400">
              <TrendingUp className="w-12 h-12 mb-4 opacity-50" />
              <p>No verification data yet</p>
              <p className="text-sm">Activity will appear here once your identity is used</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="bg-slate-800 border-slate-700 max-w-md w-full mx-4">
            <CardHeader>
              <CardTitle className="text-white flex items-center">
                <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
                Delete Identity
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-gray-400">
                Are you sure you want to delete this identity? This action cannot be undone.
                All associated data, licenses, and training will be permanently removed.
              </p>
              <div className="flex space-x-3">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setShowDeleteConfirm(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={() => deleteMutation.mutate()}
                  loading={deleteMutation.isPending}
                >
                  Delete Forever
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

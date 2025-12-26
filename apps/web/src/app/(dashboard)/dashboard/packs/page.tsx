'use client'

import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { Package, Plus, Download, Eye, Star } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { actorPackApi } from '@/lib/api'

export default function ActorPacksPage() {
  const { data: packs, isLoading } = useQuery({
    queryKey: ['public-actor-packs'],
    queryFn: () => actorPackApi.getPublic(),
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Actor Packs</h1>
          <p className="text-slate-400">
            Manage your AI-generated actor packs
          </p>
        </div>
        <Link href="/identity/register">
          <Button className="bg-purple-600 hover:bg-purple-700">
            <Plus className="w-4 h-4 mr-2" />
            Create New Pack
          </Button>
        </Link>
      </div>

      {/* Packs Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="bg-slate-800 border-slate-700 animate-pulse">
              <CardContent className="p-6">
                <div className="h-32 bg-slate-700 rounded mb-4" />
                <div className="h-4 bg-slate-700 rounded w-2/3 mb-2" />
                <div className="h-4 bg-slate-700 rounded w-1/2" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : packs?.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {packs.map((pack: any) => (
            <Card key={pack.id} className="bg-slate-800 border-slate-700 hover:border-slate-600 transition-colors">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="w-12 h-12 rounded-lg bg-purple-500/20 flex items-center justify-center">
                    <Package className="w-6 h-6 text-purple-400" />
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    pack.training_status === 'COMPLETED'
                      ? 'bg-green-500/20 text-green-400'
                      : pack.training_status === 'PROCESSING'
                      ? 'bg-blue-500/20 text-blue-400'
                      : 'bg-yellow-500/20 text-yellow-400'
                  }`}>
                    {pack.training_status}
                  </span>
                </div>
                <CardTitle className="text-white mt-4">{pack.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-400 text-sm mb-4 line-clamp-2">
                  {pack.description || 'No description'}
                </p>
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-4 text-slate-400">
                    <span className="flex items-center gap-1">
                      <Download className="w-4 h-4" />
                      {pack.total_downloads || 0}
                    </span>
                    <span className="flex items-center gap-1">
                      <Eye className="w-4 h-4" />
                      {pack.total_uses || 0}
                    </span>
                    {pack.avg_rating > 0 && (
                      <span className="flex items-center gap-1">
                        <Star className="w-4 h-4 text-yellow-400" />
                        {pack.avg_rating.toFixed(1)}
                      </span>
                    )}
                  </div>
                  <span className="text-green-400 font-semibold">
                    ${pack.base_price_usd?.toFixed(2) || '0.00'}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Package className="w-16 h-16 text-slate-600 mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No Actor Packs Yet</h3>
            <p className="text-slate-400 mb-6 text-center max-w-md">
              Create your first actor pack by registering an identity.
              Your AI-generated likeness will be available for licensing.
            </p>
            <Link href="/identity/register">
              <Button className="bg-purple-600 hover:bg-purple-700">
                <Plus className="w-4 h-4 mr-2" />
                Create Your First Pack
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

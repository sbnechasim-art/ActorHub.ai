'use client'

import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { Shield, Users, CheckCircle, Calendar } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { identityApi } from '@/lib/api'
import { getProxiedImageUrl } from '@/lib/utils'

interface GalleryIdentity {
  id: string
  display_name: string
  bio?: string
  profile_image_url?: string
  status: string
  verified_at?: string
  protection_level: string
  total_verifications: number
}

export default function GalleryPage() {
  const { data: identities, isLoading } = useQuery<GalleryIdentity[]>({
    queryKey: ['public-gallery'],
    queryFn: () => identityApi.getPublicGallery(0, 100),
  })

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-xl">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-white">ActorHub.ai</span>
          </Link>
          <nav className="flex items-center gap-6">
            <Link href="/marketplace" className="text-slate-400 hover:text-white transition">
              Marketplace
            </Link>
            <Link href="/sign-in" className="text-slate-400 hover:text-white transition">
              Sign In
            </Link>
          </nav>
        </div>
      </header>

      <main className="container mx-auto px-4 py-12">
        {/* Page Title */}
        <div className="text-center mb-12">
          <div className="w-16 h-16 rounded-full bg-purple-500/20 flex items-center justify-center mx-auto mb-6">
            <Users className="w-8 h-8 text-purple-400" />
          </div>
          <h1 className="text-4xl font-bold text-white mb-4">Public Gallery</h1>
          <p className="text-slate-400 max-w-2xl mx-auto">
            Browse verified identities who have chosen to share their profiles publicly.
            Each identity is protected by AI-powered face recognition.
          </p>
        </div>

        {/* Gallery Grid */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {[...Array(8)].map((_, i) => (
              <Card key={i} className="bg-slate-800/50 border-slate-700 animate-pulse">
                <CardContent className="p-0">
                  <div className="aspect-square bg-slate-700" />
                  <div className="p-4">
                    <div className="h-5 bg-slate-700 rounded w-3/4 mb-2" />
                    <div className="h-4 bg-slate-700 rounded w-1/2" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : identities && identities.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {identities.map((identity) => {
              const imageUrl = getProxiedImageUrl(identity.profile_image_url)
              return (
              <Link key={identity.id} href={`/identity/${identity.id}`}>
                <Card className="bg-slate-800/50 border-slate-700 hover:border-purple-500/50 transition-all duration-300 overflow-hidden group cursor-pointer">
                  <CardContent className="p-0">
                    {/* Image */}
                    <div className="aspect-square relative overflow-hidden bg-slate-900">
                      {imageUrl ? (
                        <img
                          src={imageUrl}
                          alt={identity.display_name}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Shield className="w-16 h-16 text-slate-700" />
                        </div>
                      )}

                      {/* Verified Badge */}
                      <div className="absolute top-3 right-3 bg-green-500/90 text-white text-xs font-medium px-2 py-1 rounded-full flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" />
                        Verified
                      </div>

                      {/* Protection Level Badge */}
                      <div className="absolute top-3 left-3 bg-slate-900/80 text-slate-300 text-xs font-medium px-2 py-1 rounded-full">
                        {identity.protection_level}
                      </div>
                    </div>

                    {/* Info */}
                    <div className="p-4">
                      <h3 className="font-semibold text-white text-lg mb-1 truncate">
                        {identity.display_name}
                      </h3>

                      {identity.bio && (
                        <p className="text-slate-400 text-sm line-clamp-2 mb-3">
                          {identity.bio}
                        </p>
                      )}

                      <div className="flex items-center justify-between text-xs text-slate-500">
                        <span className="flex items-center gap-1">
                          <Shield className="w-3 h-3" />
                          {identity.total_verifications} verifications
                        </span>
                        {identity.verified_at && (
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {new Date(identity.verified_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            )})}
          </div>
        ) : (
          <div className="text-center py-16">
            <Users className="w-16 h-16 text-slate-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No public identities yet</h3>
            <p className="text-slate-400 mb-6">
              Be the first to share your verified identity in the public gallery.
            </p>
            <Link
              href="/identity/register"
              className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-lg transition"
            >
              <Shield className="w-5 h-5" />
              Register Your Identity
            </Link>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-8 mt-12">
        <div className="container mx-auto px-4 text-center text-slate-500 text-sm">
          <p>Protected by ActorHub.ai - AI-Powered Identity Protection</p>
        </div>
      </footer>
    </div>
  )
}

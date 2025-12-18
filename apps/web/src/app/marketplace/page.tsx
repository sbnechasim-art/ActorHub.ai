'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Search, Filter, Grid, List, Star, Sparkles, Shield,
  Play, Users, TrendingUp, Award, ChevronRight, Mic,
  Video, Image as ImageIcon, CheckCircle, Heart
} from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { marketplaceApi } from '@/lib/api'
import { formatCurrency, cn } from '@/lib/utils'

const CATEGORIES = [
  { id: 'all', name: 'All', icon: Sparkles },
  { id: 'actor', name: 'Actors', icon: Video },
  { id: 'model', name: 'Models', icon: ImageIcon },
  { id: 'influencer', name: 'Influencers', icon: Users },
  { id: 'voice', name: 'Voice Artists', icon: Mic },
  { id: 'character', name: 'Characters', icon: Sparkles },
]

// Check if we should use mock data (development mode only)
const USE_MOCK_DATA = process.env.NEXT_PUBLIC_USE_MOCK_DATA === 'true'

// Sample featured actors - ONLY used in development with USE_MOCK_DATA=true
const FEATURED_ACTORS = USE_MOCK_DATA ? [
  {
    id: 'featured-1',
    title: 'Sarah Mitchell',
    short_description: 'Award-winning actress with 15+ years experience. Versatile performer.',
    thumbnail_url: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&h=400&fit=crop&crop=face',
    category: 'actor',
    is_featured: true,
    avg_rating: 4.9,
    rating_count: 127,
    license_count: 89,
    pricing_tiers: [{ name: 'Basic', price: 299 }],
    tags: ['Film', 'Commercial', 'Voice'],
    verified: true,
  },
  {
    id: 'featured-2',
    title: 'Michael Chen',
    short_description: 'Professional model and actor. Specializes in commercial and editorial work.',
    thumbnail_url: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop&crop=face',
    category: 'model',
    is_featured: true,
    avg_rating: 4.8,
    rating_count: 94,
    license_count: 156,
    pricing_tiers: [{ name: 'Basic', price: 199 }],
    tags: ['Commercial', 'Fashion', 'Sports'],
    verified: true,
  },
  {
    id: 'featured-3',
    title: 'Emma Rodriguez',
    short_description: 'Top voice artist with distinctive warm tone. Audiobook narrator.',
    thumbnail_url: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=400&h=400&fit=crop&crop=face',
    category: 'voice',
    is_featured: true,
    avg_rating: 5.0,
    rating_count: 203,
    license_count: 312,
    pricing_tiers: [{ name: 'Basic', price: 149 }],
    tags: ['Narration', 'Commercial', 'Animation'],
    verified: true,
  },
  {
    id: 'featured-4',
    title: 'James Wilson',
    short_description: 'Character actor known for dramatic roles. Theater background.',
    thumbnail_url: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400&h=400&fit=crop&crop=face',
    category: 'actor',
    is_featured: true,
    avg_rating: 4.7,
    rating_count: 68,
    license_count: 45,
    pricing_tiers: [{ name: 'Basic', price: 349 }],
    tags: ['Drama', 'Theater', 'Voice'],
    verified: true,
  },
] : []

// Additional sample actors - ONLY used in development with USE_MOCK_DATA=true
const SAMPLE_ACTORS = USE_MOCK_DATA ? [
  {
    id: 'actor-1',
    title: 'Alex Turner',
    short_description: 'Young actor with fresh energy. Perfect for youth-oriented content.',
    thumbnail_url: 'https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=400&h=400&fit=crop&crop=face',
    category: 'actor',
    avg_rating: 4.6,
    rating_count: 42,
    license_count: 28,
    pricing_tiers: [{ name: 'Basic', price: 149 }],
    tags: ['Youth', 'Commercial', 'Social'],
    verified: true,
  },
  {
    id: 'actor-2',
    title: 'Isabella Martinez',
    short_description: 'Bilingual actress fluent in English and Spanish. Diverse range.',
    thumbnail_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=400&fit=crop&crop=face',
    category: 'actor',
    avg_rating: 4.8,
    rating_count: 76,
    license_count: 54,
    pricing_tiers: [{ name: 'Basic', price: 249 }],
    tags: ['Bilingual', 'Commercial', 'Film'],
    verified: true,
  },
  {
    id: 'actor-3',
    title: 'David Kim',
    short_description: 'Action specialist with martial arts background. Stunt coordination.',
    thumbnail_url: 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&h=400&fit=crop&crop=face',
    category: 'actor',
    avg_rating: 4.9,
    rating_count: 89,
    license_count: 67,
    pricing_tiers: [{ name: 'Basic', price: 399 }],
    tags: ['Action', 'Stunts', 'Film'],
    verified: true,
  },
  {
    id: 'model-1',
    title: 'Sophie Anderson',
    short_description: 'High fashion model with runway experience. Editorial specialist.',
    thumbnail_url: 'https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=400&h=400&fit=crop&crop=face',
    category: 'model',
    avg_rating: 4.7,
    rating_count: 112,
    license_count: 198,
    pricing_tiers: [{ name: 'Basic', price: 279 }],
    tags: ['Fashion', 'Editorial', 'Runway'],
    verified: true,
  },
  {
    id: 'model-2',
    title: 'Marcus Johnson',
    short_description: 'Fitness model and brand ambassador. Athletic builds specialist.',
    thumbnail_url: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&h=400&fit=crop&crop=face',
    category: 'model',
    avg_rating: 4.5,
    rating_count: 58,
    license_count: 82,
    pricing_tiers: [{ name: 'Basic', price: 199 }],
    tags: ['Fitness', 'Sports', 'Commercial'],
    verified: true,
  },
  {
    id: 'voice-1',
    title: 'Rachel Green',
    short_description: 'Professional voice actress with 500+ projects. Animation expert.',
    thumbnail_url: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400&h=400&fit=crop&crop=face',
    category: 'voice',
    avg_rating: 4.9,
    rating_count: 234,
    license_count: 421,
    pricing_tiers: [{ name: 'Basic', price: 179 }],
    tags: ['Animation', 'Games', 'Audiobook'],
    verified: true,
  },
  {
    id: 'influencer-1',
    title: 'Tyler Brooks',
    short_description: 'Social media personality with 2M+ followers. Gen-Z specialist.',
    thumbnail_url: 'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=400&h=400&fit=crop&crop=face',
    category: 'influencer',
    avg_rating: 4.4,
    rating_count: 167,
    license_count: 289,
    pricing_tiers: [{ name: 'Basic', price: 129 }],
    tags: ['Social', 'Youth', 'Lifestyle'],
    verified: true,
  },
  {
    id: 'influencer-2',
    title: 'Olivia Park',
    short_description: 'Beauty and lifestyle creator. Brand collaboration expert.',
    thumbnail_url: 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=400&h=400&fit=crop&crop=face',
    category: 'influencer',
    avg_rating: 4.6,
    rating_count: 145,
    license_count: 203,
    pricing_tiers: [{ name: 'Basic', price: 159 }],
    tags: ['Beauty', 'Lifestyle', 'Fashion'],
    verified: true,
  },
] : []

function FeaturedCard({ listing }: { listing: any }) {
  const minPrice = listing.pricing_tiers?.[0]?.price || 0

  return (
    <Card className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 border-slate-700/50 overflow-hidden group hover:border-purple-500/50 transition-all duration-300 hover:shadow-xl hover:shadow-purple-500/10">
      <div className="relative">
        <div className="aspect-[4/5] relative overflow-hidden">
          <img
            src={listing.thumbnail_url}
            alt={listing.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-transparent to-transparent" />

          {/* Featured Badge */}
          <div className="absolute top-3 left-3 flex items-center gap-1.5 px-2.5 py-1 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xs font-bold rounded-full shadow-lg">
            <Award className="w-3 h-3" />
            Featured
          </div>

          {/* Verified Badge */}
          {listing.verified && (
            <div className="absolute top-3 right-3 flex items-center gap-1 px-2 py-1 bg-blue-500/90 backdrop-blur-sm text-white text-xs font-medium rounded-full">
              <CheckCircle className="w-3 h-3" />
              Verified
            </div>
          )}

          {/* Quick Stats Overlay */}
          <div className="absolute bottom-0 left-0 right-0 p-4">
            <h3 className="font-bold text-xl text-white mb-1">{listing.title}</h3>
            <p className="text-sm text-slate-300 line-clamp-2 mb-3">
              {listing.short_description}
            </p>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1 text-yellow-400">
                  <Star className="w-4 h-4 fill-current" />
                  <span className="text-sm font-semibold">{listing.avg_rating}</span>
                  <span className="text-xs text-slate-400">({listing.rating_count})</span>
                </div>
                <div className="text-xs text-slate-400">
                  {listing.license_count} licenses
                </div>
              </div>
              <div className="text-right">
                <span className="text-lg font-bold text-white">
                  {formatCurrency(minPrice)}
                </span>
                <span className="text-slate-400 text-xs ml-1">from</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}

function ListingCard({ listing }: { listing: any }) {
  const minPrice = listing.pricing_tiers?.[0]?.price || 0
  const [isLiked, setIsLiked] = useState(false)

  return (
    <Card className="bg-slate-800/50 border-slate-700/50 overflow-hidden group hover:border-slate-600 hover:shadow-lg transition-all duration-300">
      <div className="aspect-square relative overflow-hidden">
        {listing.thumbnail_url ? (
          <img
            src={listing.thumbnail_url}
            alt={listing.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
            <Sparkles className="w-12 h-12 text-white/50" />
          </div>
        )}

        {/* Gradient Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

        {/* Verified Badge */}
        {listing.verified && (
          <div className="absolute top-2 left-2 flex items-center gap-1 px-2 py-0.5 bg-blue-500/90 backdrop-blur-sm text-white text-xs font-medium rounded-full">
            <CheckCircle className="w-3 h-3" />
            Verified
          </div>
        )}

        {/* Like Button */}
        <button
          onClick={(e) => { e.preventDefault(); setIsLiked(!isLiked); }}
          className="absolute top-2 right-2 w-8 h-8 rounded-full bg-slate-900/70 backdrop-blur-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300 hover:bg-slate-900"
        >
          <Heart className={cn("w-4 h-4 transition-colors", isLiked ? "fill-red-500 text-red-500" : "text-white")} />
        </button>

        {/* Quick View Button */}
        <div className="absolute bottom-3 left-3 right-3 opacity-0 group-hover:opacity-100 transition-all duration-300 transform translate-y-2 group-hover:translate-y-0">
          <Button size="sm" className="w-full bg-purple-600 hover:bg-purple-700 text-white">
            <Play className="w-3 h-3 mr-1" />
            View Profile
          </Button>
        </div>
      </div>

      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-2">
          <h3 className="font-semibold text-white truncate flex-1">{listing.title}</h3>
          {listing.avg_rating && (
            <div className="flex items-center gap-1 text-yellow-400 ml-2">
              <Star className="w-3.5 h-3.5 fill-current" />
              <span className="text-sm font-medium">{listing.avg_rating.toFixed(1)}</span>
            </div>
          )}
        </div>

        <p className="text-sm text-slate-400 mb-3 line-clamp-2">
          {listing.short_description || listing.description}
        </p>

        <div className="flex flex-wrap gap-1.5 mb-3">
          {listing.tags?.slice(0, 3).map((tag: string) => (
            <span
              key={tag}
              className="px-2 py-0.5 bg-slate-700/50 rounded-full text-xs text-slate-300"
            >
              {tag}
            </span>
          ))}
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-slate-700/50">
          <div>
            <span className="text-lg font-bold text-white">
              {formatCurrency(minPrice)}
            </span>
            <span className="text-slate-500 text-xs ml-1">/ use</span>
          </div>
          <span className="text-xs text-slate-500">
            {listing.license_count || 0} licenses sold
          </span>
        </div>
      </CardContent>
    </Card>
  )
}

export default function MarketplacePage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')

  // Fetch all listings from API
  const { data: apiListings, isLoading } = useQuery({
    queryKey: ['listings', selectedCategory, searchQuery],
    queryFn: () => marketplaceApi.getListings({
      category: selectedCategory !== 'all' ? selectedCategory : undefined,
      query: searchQuery || undefined,
    }),
  })

  // Fetch featured listings from API
  const { data: featuredListings } = useQuery({
    queryKey: ['featured-listings'],
    queryFn: () => marketplaceApi.getListings({ featured: true, limit: 4 }),
  })

  // Use API data, only fallback to sample data if USE_MOCK_DATA is true and no API data
  const allListings = apiListings?.length ? apiListings : (USE_MOCK_DATA ? SAMPLE_ACTORS : [])
  const featuredActors = featuredListings?.length ? featuredListings : (USE_MOCK_DATA ? FEATURED_ACTORS : [])

  // Filter by category
  const filteredListings = selectedCategory === 'all'
    ? allListings
    : allListings.filter(l => l.category === selectedCategory)

  // Filter by search query
  const searchedListings = searchQuery
    ? filteredListings.filter(l =>
        l.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        l.short_description?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : filteredListings

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-xl sticky top-0 z-40">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-white">ActorHub.ai</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/dashboard">
              <Button variant="ghost" className="text-slate-400 hover:text-white">Dashboard</Button>
            </Link>
            <Link href="/sign-in">
              <Button className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white">
                Sign In
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* Hero Section */}
        <section className="relative py-16 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-600/10 via-purple-600/10 to-pink-600/10" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-purple-900/20 via-transparent to-transparent" />

          <div className="container mx-auto px-4 relative">
            <div className="text-center max-w-3xl mx-auto mb-12">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-400 text-sm mb-6">
                <Sparkles className="w-4 h-4" />
                Over 10,000+ AI-Ready Actor Packs
              </div>
              <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
                Actor Pack <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">Marketplace</span>
              </h1>
              <p className="text-lg text-slate-400">
                License authentic AI-ready identities for your creative projects.
                All actors are verified and creator-approved.
              </p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto mb-12">
              {[
                { label: 'Verified Actors', value: '10,000+', icon: Users },
                { label: 'Licenses Sold', value: '50,000+', icon: Shield },
                { label: 'Average Rating', value: '4.8', icon: Star },
                { label: 'Creator Earnings', value: '$2M+', icon: TrendingUp },
              ].map((stat) => (
                <div key={stat.label} className="text-center p-4 rounded-xl bg-slate-800/30 border border-slate-700/50">
                  <stat.icon className="w-5 h-5 text-purple-400 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-white">{stat.value}</div>
                  <div className="text-xs text-slate-500">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Featured Actors */}
        <section className="py-8 border-b border-slate-800/50">
          <div className="container mx-auto px-4">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                  <Award className="w-6 h-6 text-amber-400" />
                  Featured Actors
                </h2>
                <p className="text-slate-400 text-sm mt-1">Top-rated creators handpicked by our team</p>
              </div>
              <Button variant="ghost" className="text-purple-400 hover:text-purple-300">
                View All <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {featuredActors.map((actor: any) => (
                <Link key={actor.id} href={`/marketplace/${actor.id}`}>
                  <FeaturedCard listing={actor} />
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* Main Content */}
        <section className="py-8">
          <div className="container mx-auto px-4">
            {/* Search & Filters */}
            <div className="flex flex-col md:flex-row gap-4 mb-8">
              <div className="relative flex-1">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <Input
                  placeholder="Search actors, models, voice artists..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-12 h-12 bg-slate-800/50 border-slate-700/50 text-white placeholder:text-slate-500 focus:border-purple-500/50 rounded-xl"
                />
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="icon" className="h-12 w-12 border-slate-700/50 hover:bg-slate-800/50 rounded-xl">
                  <Filter className="w-5 h-5" />
                </Button>
                <Button
                  variant={viewMode === 'grid' ? 'secondary' : 'outline'}
                  size="icon"
                  onClick={() => setViewMode('grid')}
                  className="h-12 w-12 border-slate-700/50 hover:bg-slate-800/50 rounded-xl"
                >
                  <Grid className="w-5 h-5" />
                </Button>
                <Button
                  variant={viewMode === 'list' ? 'secondary' : 'outline'}
                  size="icon"
                  onClick={() => setViewMode('list')}
                  className="h-12 w-12 border-slate-700/50 hover:bg-slate-800/50 rounded-xl"
                >
                  <List className="w-5 h-5" />
                </Button>
              </div>
            </div>

            {/* Categories */}
            <div className="flex gap-2 overflow-x-auto pb-4 mb-8 scrollbar-hide">
              {CATEGORIES.map((cat) => {
                const IconComponent = cat.icon
                return (
                  <Button
                    key={cat.id}
                    variant={selectedCategory === cat.id ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSelectedCategory(cat.id)}
                    className={cn(
                      "whitespace-nowrap rounded-full px-4",
                      selectedCategory === cat.id
                        ? "bg-gradient-to-r from-blue-500 to-purple-600 text-white border-0"
                        : "border-slate-700/50 hover:bg-slate-800/50"
                    )}
                  >
                    <IconComponent className="w-4 h-4 mr-2" />
                    {cat.name}
                  </Button>
                )
              })}
            </div>

            {/* Results Count */}
            <div className="flex items-center justify-between mb-6">
              <p className="text-slate-400">
                Showing <span className="text-white font-medium">{searchedListings.length}</span> results
              </p>
              <select className="bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-300">
                <option>Most Popular</option>
                <option>Newest</option>
                <option>Price: Low to High</option>
                <option>Price: High to Low</option>
                <option>Highest Rated</option>
              </select>
            </div>

            {/* Listings Grid */}
            {isLoading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {[...Array(8)].map((_, i) => (
                  <Card key={i} className="bg-slate-800/50 border-slate-700/50 overflow-hidden">
                    <div className="aspect-square bg-slate-700/50 animate-pulse" />
                    <CardContent className="p-4 space-y-3">
                      <div className="h-5 bg-slate-700/50 rounded animate-pulse w-3/4" />
                      <div className="h-4 bg-slate-700/50 rounded animate-pulse w-full" />
                      <div className="h-4 bg-slate-700/50 rounded animate-pulse w-1/2" />
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : searchedListings.length > 0 ? (
              <div className={cn(
                viewMode === 'grid'
                  ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'
                  : 'space-y-4'
              )}>
                {searchedListings.map((listing: any) => (
                  <Link key={listing.id} href={`/marketplace/${listing.id}`}>
                    <ListingCard listing={listing} />
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-20">
                <div className="w-20 h-20 rounded-full bg-slate-800/50 flex items-center justify-center mx-auto mb-4">
                  <Search className="w-10 h-10 text-slate-600" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">No actors found</h3>
                <p className="text-slate-400 mb-6">Try adjusting your search or filters</p>
                <Button
                  onClick={() => { setSearchQuery(''); setSelectedCategory('all'); }}
                  className="bg-purple-600 hover:bg-purple-700"
                >
                  Clear Filters
                </Button>
              </div>
            )}
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-16 border-t border-slate-800/50">
          <div className="container mx-auto px-4">
            <Card className="bg-gradient-to-r from-blue-600/20 via-purple-600/20 to-pink-600/20 border-purple-500/30 overflow-hidden relative">
              <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_right,_var(--tw-gradient-stops))] from-purple-600/20 via-transparent to-transparent" />
              <CardContent className="p-8 md:p-12 relative">
                <div className="max-w-2xl">
                  <h2 className="text-3xl font-bold text-white mb-4">
                    Ready to Protect Your Identity?
                  </h2>
                  <p className="text-slate-300 mb-6">
                    Join thousands of creators who are protecting their likeness and earning passive income through licensed AI usage.
                  </p>
                  <div className="flex flex-col sm:flex-row gap-4">
                    <Link href="/sign-up">
                      <Button size="lg" className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white">
                        Get Started Free
                        <ChevronRight className="w-4 h-4 ml-2" />
                      </Button>
                    </Link>
                    <Link href="/developers">
                      <Button size="lg" variant="outline" className="border-slate-600 text-white hover:bg-slate-800">
                        View API Docs
                      </Button>
                    </Link>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/50 py-8">
        <div className="container mx-auto px-4 text-center text-slate-500 text-sm">
          © 2025 ActorHub.ai. All rights reserved.
        </div>
      </footer>
    </div>
  )
}

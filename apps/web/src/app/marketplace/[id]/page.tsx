'use client'

import { useState, useRef, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import {
  Shield, Star, CheckCircle, Play, Download, Share2,
  Heart, Eye, Award,
  Mic, Video, ImageIcon, Globe, DollarSign,
  ShoppingCart, Zap, MessageSquare, ArrowLeft, X,
  Copy, Check, Mail, Twitter, Facebook, Linkedin, Loader2
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { CartButton } from '@/components/cart'
import { useCartStore } from '@/store/cart'
import { marketplaceApi, api } from '@/lib/api'
import { formatCurrency, cn, getProxiedImageUrl } from '@/lib/utils'
import { logger } from '@/lib/logger'

// Sample actor data (same as marketplace page for demo consistency)
const SAMPLE_ACTORS: Record<string, any> = {
  'featured-1': {
    id: 'featured-1',
    title: 'Sarah Mitchell',
    short_description: 'Award-winning actress with 15+ years experience. Versatile performer.',
    description: 'Sarah Mitchell is an award-winning actress with over 15 years of experience in film, television, and theater. Known for her versatile performances and ability to embody complex characters, Sarah has worked with major studios and independent productions alike. Her AI-ready Actor Pack includes high-fidelity face models, voice synthesis, and motion capture data perfect for commercials, films, and digital content creation.',
    thumbnail_url: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=800&h=800&fit=crop&crop=face',
    gallery: [
      'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=600&h=400&fit=crop',
      'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=600&h=400&fit=crop',
      'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=600&h=400&fit=crop',
    ],
    category: 'actor',
    is_featured: true,
    avg_rating: 4.9,
    rating_count: 127,
    license_count: 89,
    view_count: 12450,
    pricing_tiers: [
      { name: 'Basic', price: 299, features: ['10 AI generations', 'Personal use only', 'Standard quality', '30 day license'] },
      { name: 'Pro', price: 599, features: ['100 AI generations', 'Commercial use', 'HD quality', 'Voice included', '90 day license'] },
      { name: 'Enterprise', price: 1499, features: ['Unlimited generations', 'Full commercial rights', '4K quality', 'Voice + Motion', '1 year license', 'Priority support'] },
    ],
    tags: ['Film', 'Commercial', 'Voice', 'Drama', 'Comedy'],
    verified: true,
    languages: ['English', 'French'],
    available_components: ['Face', 'Voice', 'Motion'],
    demo_video_url: 'https://www.youtube.com/embed/dQw4w9WgXcQ',
  },
  'featured-2': {
    id: 'featured-2',
    title: 'Michael Chen',
    short_description: 'Professional model and actor. Specializes in commercial and editorial work.',
    description: 'Michael Chen is a professional model and actor based in Los Angeles. With a background in commercial modeling and editorial photography, Michael brings a polished, camera-ready presence to every project. His Actor Pack is ideal for fashion brands, lifestyle content, and corporate communications.',
    thumbnail_url: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&h=800&fit=crop&crop=face',
    gallery: [
      'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&h=400&fit=crop',
      'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=600&h=400&fit=crop',
      'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=600&h=400&fit=crop',
    ],
    category: 'model',
    is_featured: true,
    avg_rating: 4.8,
    rating_count: 94,
    license_count: 156,
    view_count: 9823,
    pricing_tiers: [
      { name: 'Basic', price: 199, features: ['10 AI generations', 'Personal use only', 'Standard quality', '30 day license'] },
      { name: 'Pro', price: 499, features: ['100 AI generations', 'Commercial use', 'HD quality', '90 day license'] },
      { name: 'Enterprise', price: 1299, features: ['Unlimited generations', 'Full commercial rights', '4K quality', '1 year license'] },
    ],
    tags: ['Commercial', 'Fashion', 'Sports', 'Lifestyle'],
    verified: true,
    languages: ['English', 'Mandarin'],
    available_components: ['Face', 'Motion'],
  },
  'featured-3': {
    id: 'featured-3',
    title: 'Emma Rodriguez',
    short_description: 'Top voice artist with distinctive warm tone. Audiobook narrator.',
    description: 'Emma Rodriguez is a top voice artist known for her distinctive warm tone and versatile vocal range. With over 500 audiobook narrations and countless commercial voiceovers, Emma brings professionalism and emotional depth to every project. Her voice model is perfect for narration, animation, and advertising.',
    thumbnail_url: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=800&h=800&fit=crop&crop=face',
    gallery: [
      'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=600&h=400&fit=crop',
      'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=600&h=400&fit=crop',
    ],
    category: 'voice',
    is_featured: true,
    avg_rating: 5.0,
    rating_count: 203,
    license_count: 312,
    view_count: 18920,
    pricing_tiers: [
      { name: 'Basic', price: 149, features: ['5 minutes of audio', 'Personal use only', 'Standard quality'] },
      { name: 'Pro', price: 399, features: ['30 minutes of audio', 'Commercial use', 'HD quality', 'Multiple emotions'] },
      { name: 'Enterprise', price: 999, features: ['Unlimited audio', 'Full commercial rights', 'Studio quality', 'Custom training'] },
    ],
    tags: ['Narration', 'Commercial', 'Animation', 'Audiobook'],
    verified: true,
    languages: ['English', 'Spanish'],
    available_components: ['Voice'],
  },
  'featured-4': {
    id: 'featured-4',
    title: 'James Wilson',
    short_description: 'Character actor known for dramatic roles. Theater background.',
    description: 'James Wilson is a seasoned character actor with extensive theater and film experience. Known for his dramatic intensity and ability to transform into complex characters, James brings gravitas to any production. His Actor Pack is ideal for dramatic content, period pieces, and narrative-driven projects.',
    thumbnail_url: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=800&h=800&fit=crop&crop=face',
    gallery: [
      'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=600&h=400&fit=crop',
      'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=600&h=400&fit=crop',
    ],
    category: 'actor',
    is_featured: true,
    avg_rating: 4.7,
    rating_count: 68,
    license_count: 45,
    view_count: 5632,
    pricing_tiers: [
      { name: 'Basic', price: 349, features: ['10 AI generations', 'Personal use only', 'Standard quality', '30 day license'] },
      { name: 'Pro', price: 699, features: ['100 AI generations', 'Commercial use', 'HD quality', 'Voice included', '90 day license'] },
      { name: 'Enterprise', price: 1799, features: ['Unlimited generations', 'Full commercial rights', '4K quality', 'Voice + Motion', '1 year license'] },
    ],
    tags: ['Drama', 'Theater', 'Voice', 'Period'],
    verified: true,
    languages: ['English'],
    available_components: ['Face', 'Voice', 'Motion'],
  },
}

// Add remaining sample actors (abbreviated for brevity)
Object.assign(SAMPLE_ACTORS, {
  'actor-1': { id: 'actor-1', title: 'Alex Turner', category: 'actor', thumbnail_url: 'https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=800&h=800&fit=crop&crop=face', avg_rating: 4.6, rating_count: 42, license_count: 28, view_count: 3421, pricing_tiers: [{ name: 'Basic', price: 149, features: ['10 AI generations'] }], tags: ['Youth'], verified: true, languages: ['English'], available_components: ['Face'] },
  'actor-2': { id: 'actor-2', title: 'Isabella Martinez', category: 'actor', thumbnail_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&h=800&fit=crop&crop=face', avg_rating: 4.8, rating_count: 76, license_count: 54, view_count: 6789, pricing_tiers: [{ name: 'Basic', price: 249, features: ['10 AI generations'] }], tags: ['Bilingual'], verified: true, languages: ['English', 'Spanish'], available_components: ['Face', 'Voice'] },
  'actor-3': { id: 'actor-3', title: 'David Kim', category: 'actor', thumbnail_url: 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=800&h=800&fit=crop&crop=face', avg_rating: 4.9, rating_count: 89, license_count: 67, view_count: 8234, pricing_tiers: [{ name: 'Basic', price: 399, features: ['10 AI generations'] }], tags: ['Action'], verified: true, languages: ['English', 'Korean'], available_components: ['Face', 'Motion'] },
  'model-1': { id: 'model-1', title: 'Sophie Anderson', category: 'model', thumbnail_url: 'https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=800&h=800&fit=crop&crop=face', avg_rating: 4.7, rating_count: 112, license_count: 198, view_count: 14532, pricing_tiers: [{ name: 'Basic', price: 279, features: ['10 AI generations'] }], tags: ['Fashion'], verified: true, languages: ['English'], available_components: ['Face'] },
  'model-2': { id: 'model-2', title: 'Marcus Johnson', category: 'model', thumbnail_url: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=800&h=800&fit=crop&crop=face', avg_rating: 4.5, rating_count: 58, license_count: 82, view_count: 5678, pricing_tiers: [{ name: 'Basic', price: 199, features: ['10 AI generations'] }], tags: ['Fitness'], verified: true, languages: ['English'], available_components: ['Face', 'Motion'] },
  'voice-1': { id: 'voice-1', title: 'Rachel Green', category: 'voice', thumbnail_url: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=800&h=800&fit=crop&crop=face', avg_rating: 4.9, rating_count: 234, license_count: 421, view_count: 22341, pricing_tiers: [{ name: 'Basic', price: 179, features: ['5 minutes of audio'] }], tags: ['Animation'], verified: true, languages: ['English'], available_components: ['Voice'] },
  'influencer-1': { id: 'influencer-1', title: 'Tyler Brooks', category: 'influencer', thumbnail_url: 'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=800&h=800&fit=crop&crop=face', avg_rating: 4.4, rating_count: 167, license_count: 289, view_count: 19823, pricing_tiers: [{ name: 'Basic', price: 129, features: ['10 AI generations'] }], tags: ['Social'], verified: true, languages: ['English'], available_components: ['Face'] },
  'influencer-2': { id: 'influencer-2', title: 'Olivia Park', category: 'influencer', thumbnail_url: 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=800&h=800&fit=crop&crop=face', avg_rating: 4.6, rating_count: 145, license_count: 203, view_count: 16432, pricing_tiers: [{ name: 'Basic', price: 159, features: ['10 AI generations'] }], tags: ['Beauty'], verified: true, languages: ['English', 'Korean'], available_components: ['Face'] },
})

function ComponentBadge({ component }: { component: string }) {
  const icons: Record<string, any> = {
    Face: ImageIcon,
    Voice: Mic,
    Motion: Video,
  }
  const Icon = icons[component] || Zap

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-slate-800/50 rounded-lg border border-slate-700/50">
      <Icon className="w-4 h-4 text-purple-400" />
      <span className="text-sm text-slate-300">{component}</span>
    </div>
  )
}

function PricingCard({
  tier,
  isPopular,
  actor
}: {
  tier: any;
  isPopular: boolean;
  actor: any;
}) {
  const { addItem } = useCartStore()

  const handleAddToCart = () => {
    addItem({
      id: `${actor.id}-${tier.name}-${Date.now()}`,
      actorId: actor.id,
      identityId: actor.identity_id,
      actorName: actor.title,
      actorImage: actor.thumbnail_url,
      tierName: tier.name,
      tierPrice: tier.price,
      features: tier.features,
    })
  }

  return (
    <Card className={cn(
      "relative overflow-hidden transition-all duration-300 hover:scale-[1.02]",
      isPopular
        ? "bg-gradient-to-br from-purple-900/50 to-slate-900 border-purple-500/50 shadow-lg shadow-purple-500/10"
        : "bg-slate-800/50 border-slate-700/50"
    )}>
      {isPopular && (
        <div className="absolute top-0 right-0 px-3 py-1 bg-gradient-to-r from-purple-500 to-pink-500 text-white text-xs font-bold rounded-bl-lg">
          Most Popular
        </div>
      )}
      <CardHeader className="pb-2">
        <CardTitle className="text-white text-xl">{tier.name}</CardTitle>
        <div className="mt-2">
          <span className="text-4xl font-bold text-white">{formatCurrency(tier.price)}</span>
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        <ul className="space-y-3 mb-6">
          {tier.features.map((feature: string, i: number) => (
            <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
              <CheckCircle className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
              {feature}
            </li>
          ))}
        </ul>
        <Button
          onClick={handleAddToCart}
          className={cn(
            "w-full",
            isPopular
              ? "bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
              : "bg-slate-700 hover:bg-slate-600"
          )}
        >
          <ShoppingCart className="w-4 h-4 mr-2" />
          Add to Cart
        </Button>
      </CardContent>
    </Card>
  )
}

// Share Modal Component
function ShareModal({ isOpen, onClose, actor }: { isOpen: boolean; onClose: () => void; actor: any }) {
  const [copied, setCopied] = useState(false)
  const shareUrl = typeof window !== 'undefined' ? window.location.href : ''

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      logger.error('Failed to copy URL', err as Error)
    }
  }

  const shareLinks = [
    { name: 'Twitter', icon: Twitter, url: `https://twitter.com/intent/tweet?text=Check out ${actor.title} on ActorHub.ai&url=${encodeURIComponent(shareUrl)}` },
    { name: 'Facebook', icon: Facebook, url: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}` },
    { name: 'LinkedIn', icon: Linkedin, url: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}` },
    { name: 'Email', icon: Mail, url: `mailto:?subject=Check out ${actor.title} on ActorHub.ai&body=${encodeURIComponent(shareUrl)}` },
  ]

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <Card className="bg-slate-800 border-slate-700 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-white">Share {actor.title}</CardTitle>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-5 h-5 text-slate-400" />
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-3 justify-center">
            {shareLinks.map((link) => (
              <a
                key={link.name}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="w-12 h-12 rounded-full bg-slate-700 hover:bg-slate-600 flex items-center justify-center transition-colors"
                aria-label={`Share on ${link.name}`}
              >
                <link.icon className="w-5 h-5 text-slate-300" />
              </a>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              value={shareUrl}
              readOnly
              className="bg-slate-900 border-slate-600 text-slate-300"
            />
            <Button onClick={copyToClipboard} className="bg-purple-600 hover:bg-purple-700">
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// Contact Modal Component
function ContactModal({ isOpen, onClose, actor }: { isOpen: boolean; onClose: () => void; actor: any }) {
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)

  const handleSend = async () => {
    setSending(true)
    try {
      // API call to send contact message
      await api.post('/marketplace/contact', {
        listing_id: actor.id,
        message,
      })
      setSent(true)
      setTimeout(() => {
        onClose()
        setSent(false)
        setMessage('')
      }, 2000)
    } catch (err) {
      logger.error('Failed to send message', err as Error)
    } finally {
      setSending(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <Card className="bg-slate-800 border-slate-700 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-white">Contact {actor.title}</CardTitle>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-5 h-5 text-slate-400" />
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {sent ? (
            <div className="text-center py-8">
              <Check className="w-12 h-12 text-green-400 mx-auto mb-3" />
              <p className="text-white font-medium">Message sent!</p>
              <p className="text-slate-400 text-sm">You'll receive a response soon.</p>
            </div>
          ) : (
            <>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Write your message..."
                className="w-full h-32 bg-slate-900 border border-slate-600 rounded-lg p-3 text-white placeholder-slate-500 resize-none focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
              <div className="flex gap-3">
                <Button variant="outline" className="flex-1 border-slate-600" onClick={onClose}>
                  Cancel
                </Button>
                <Button
                  className="flex-1 bg-purple-600 hover:bg-purple-700"
                  onClick={handleSend}
                  disabled={!message.trim() || sending}
                >
                  {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Send Message'}
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

// Preview Demo Modal
function PreviewModal({ isOpen, onClose, actor }: { isOpen: boolean; onClose: () => void; actor: any }) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={onClose}>
      <div className="relative max-w-4xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
        <Button
          variant="ghost"
          size="icon"
          className="absolute -top-12 right-0 text-white hover:bg-white/10"
          onClick={onClose}
        >
          <X className="w-6 h-6" />
        </Button>
        <Card className="bg-slate-800 border-slate-700 overflow-hidden">
          <CardContent className="p-0">
            {actor.demo_video_url ? (
              <div className="aspect-video">
                <iframe
                  src={actor.demo_video_url}
                  className="w-full h-full"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              </div>
            ) : (
              <div className="aspect-video flex items-center justify-center bg-slate-900">
                <div className="text-center">
                  <Play className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                  <p className="text-slate-400 text-lg">Demo preview coming soon</p>
                  <p className="text-slate-500 text-sm mt-2">
                    Sample AI-generated content for {actor.title} will be available shortly.
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default function ActorDetailPage() {
  const params = useParams()
  const id = params.id as string
  const queryClient = useQueryClient()
  const pricingSectionRef = useRef<HTMLElement>(null)

  const [selectedImage, setSelectedImage] = useState(0)
  const [isLiked, setIsLiked] = useState(false)
  const [showShareModal, setShowShareModal] = useState(false)
  const [showContactModal, setShowContactModal] = useState(false)
  const [showPreviewModal, setShowPreviewModal] = useState(false)

  // Try to get from API first, fallback to sample data
  const { data: apiActor, isLoading } = useQuery({
    queryKey: ['listing', id],
    queryFn: () => marketplaceApi.getListing(id),
    retry: false,
  })

  // Check if user has favorited this listing
  const { data: favoritesData } = useQuery({
    queryKey: ['favorites'],
    queryFn: () => api.get('/marketplace/favorites').then(r => r.data),
    retry: false,
  })

  // Update isLiked when favorites data loads
  useEffect(() => {
    if (favoritesData?.favorites) {
      setIsLiked(favoritesData.favorites.some((f: any) => f.listing_id === id))
    }
  }, [favoritesData, id])

  // Toggle favorite mutation
  const toggleFavoriteMutation = useMutation({
    mutationFn: async () => {
      if (isLiked) {
        return api.delete(`/marketplace/favorites/${id}`)
      } else {
        return api.post('/marketplace/favorites', { listing_id: id })
      }
    },
    onSuccess: () => {
      setIsLiked(!isLiked)
      queryClient.invalidateQueries({ queryKey: ['favorites'] })
    },
    onError: (err) => {
      logger.error('Failed to toggle favorite', err as Error)
    },
  })

  const handleLikeClick = () => {
    toggleFavoriteMutation.mutate()
  }

  const scrollToPricing = () => {
    pricingSectionRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // Use API data or sample data
  const actor = apiActor || SAMPLE_ACTORS[id]

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  if (!actor) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white mb-4">Actor Not Found</h1>
          <p className="text-slate-400 mb-6">The actor you're looking for doesn't exist.</p>
          <Link href="/marketplace">
            <Button className="bg-purple-600 hover:bg-purple-700">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Marketplace
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  const rawGallery = actor.gallery || [actor.thumbnail_url]
  const gallery = rawGallery.map((url: string) => getProxiedImageUrl(url) || url)

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-xl sticky top-0 z-40">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/marketplace" className="flex items-center gap-2 text-slate-400 hover:text-white transition">
              <ArrowLeft className="w-5 h-5" />
              <span className="hidden sm:inline">Back to Marketplace</span>
            </Link>
          </div>
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-white">ActorHub.ai</span>
          </Link>
          <div className="flex items-center gap-2">
            <CartButton />
            <Button
              variant="ghost"
              size="icon"
              onClick={handleLikeClick}
              disabled={toggleFavoriteMutation.isPending}
            >
              {toggleFavoriteMutation.isPending ? (
                <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
              ) : (
                <Heart className={cn("w-5 h-5", isLiked ? "fill-red-500 text-red-500" : "text-slate-400")} />
              )}
            </Button>
            <Button variant="ghost" size="icon" onClick={() => setShowShareModal(true)}>
              <Share2 className="w-5 h-5 text-slate-400" />
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-2 gap-8 mb-12">
          {/* Gallery */}
          <div className="space-y-4">
            <div className="aspect-square relative rounded-2xl overflow-hidden bg-slate-800">
              <img
                src={gallery[selectedImage]}
                alt={actor.title}
                className="w-full h-full object-cover"
              />
              {actor.is_featured && (
                <div className="absolute top-4 left-4 flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-sm font-bold rounded-full shadow-lg">
                  <Award className="w-4 h-4" />
                  Featured
                </div>
              )}
              {actor.verified && (
                <div className="absolute top-4 right-4 flex items-center gap-1.5 px-3 py-1.5 bg-blue-500/90 backdrop-blur-sm text-white text-sm font-medium rounded-full">
                  <CheckCircle className="w-4 h-4" />
                  Verified
                </div>
              )}
            </div>

            {gallery.length > 1 && (
              <div className="flex gap-2 overflow-x-auto pb-2">
                {gallery.map((img: string, i: number) => (
                  <button
                    key={i}
                    onClick={() => setSelectedImage(i)}
                    className={cn(
                      "w-20 h-20 rounded-lg overflow-hidden flex-shrink-0 border-2 transition-all",
                      selectedImage === i ? "border-purple-500" : "border-transparent opacity-60 hover:opacity-100"
                    )}
                  >
                    <img src={img} alt="" className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Info */}
          <div className="space-y-6">
            <div>
              <div className="flex items-center gap-2 text-sm text-purple-400 mb-2">
                <span className="capitalize">{actor.category}</span>
                <span>•</span>
                <span>{actor.license_count} licenses sold</span>
              </div>
              <h1 className="text-4xl font-bold text-white mb-4">{actor.title}</h1>
              <p className="text-lg text-slate-400">{actor.description || actor.short_description}</p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-4 rounded-xl bg-slate-800/50 border border-slate-700/50">
                <div className="flex items-center justify-center gap-1 text-yellow-400 mb-1">
                  <Star className="w-5 h-5 fill-current" />
                  <span className="text-xl font-bold">{actor.avg_rating}</span>
                </div>
                <div className="text-xs text-slate-500">{actor.rating_count} reviews</div>
              </div>
              <div className="text-center p-4 rounded-xl bg-slate-800/50 border border-slate-700/50">
                <div className="flex items-center justify-center gap-1 text-blue-400 mb-1">
                  <Download className="w-5 h-5" />
                  <span className="text-xl font-bold">{actor.license_count}</span>
                </div>
                <div className="text-xs text-slate-500">Licenses</div>
              </div>
              <div className="text-center p-4 rounded-xl bg-slate-800/50 border border-slate-700/50">
                <div className="flex items-center justify-center gap-1 text-green-400 mb-1">
                  <Eye className="w-5 h-5" />
                  <span className="text-xl font-bold">{(actor.view_count / 1000).toFixed(1)}k</span>
                </div>
                <div className="text-xs text-slate-500">Views</div>
              </div>
            </div>

            {/* Available Components */}
            <div>
              <h3 className="text-sm font-medium text-slate-400 mb-3">Available Components</h3>
              <div className="flex flex-wrap gap-2">
                {(actor.available_components || ['Face']).map((comp: string) => (
                  <ComponentBadge key={comp} component={comp} />
                ))}
              </div>
            </div>

            {/* Languages */}
            {actor.languages && (
              <div>
                <h3 className="text-sm font-medium text-slate-400 mb-3">Languages</h3>
                <div className="flex flex-wrap gap-2">
                  {actor.languages.map((lang: string) => (
                    <div key={lang} className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/50 rounded-full border border-slate-700/50">
                      <Globe className="w-3.5 h-3.5 text-slate-400" />
                      <span className="text-sm text-slate-300">{lang}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tags */}
            <div>
              <h3 className="text-sm font-medium text-slate-400 mb-3">Tags</h3>
              <div className="flex flex-wrap gap-2">
                {actor.tags?.map((tag: string) => (
                  <span key={tag} className="px-3 py-1 bg-purple-500/10 border border-purple-500/20 rounded-full text-sm text-purple-300">
                    {tag}
                  </span>
                ))}
              </div>
            </div>

            {/* Quick Action */}
            <div className="flex gap-3">
              <Button
                size="lg"
                className="flex-1 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700"
                onClick={() => setShowPreviewModal(true)}
              >
                <Play className="w-5 h-5 mr-2" />
                Preview Demo
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="border-slate-700"
                onClick={() => setShowContactModal(true)}
              >
                <MessageSquare className="w-5 h-5 mr-2" />
                Contact
              </Button>
            </div>
          </div>
        </div>

        {/* Pricing Section */}
        <section ref={pricingSectionRef} className="mb-12">
          <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
            <DollarSign className="w-6 h-6 text-green-400" />
            Licensing Options
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {actor.pricing_tiers?.map((tier: any, i: number) => (
              <PricingCard key={tier.name} tier={tier} isPopular={i === 1} actor={actor} />
            ))}
          </div>
        </section>

        {/* Reviews Section Placeholder */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
            <Star className="w-6 h-6 text-yellow-400" />
            Reviews ({actor.rating_count})
          </h2>
          <Card className="bg-slate-800/50 border-slate-700/50">
            <CardContent className="p-8 text-center">
              <p className="text-slate-400">Reviews coming soon</p>
            </CardContent>
          </Card>
        </section>

        {/* CTA */}
        <section>
          <Card className="bg-gradient-to-r from-blue-600/20 via-purple-600/20 to-pink-600/20 border-purple-500/30">
            <CardContent className="p-8 text-center">
              <h2 className="text-2xl font-bold text-white mb-4">Ready to License {actor.title}?</h2>
              <p className="text-slate-300 mb-6">Choose a plan above to get started with AI-generated content using this verified identity.</p>
              <Button
                size="lg"
                className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700"
                onClick={scrollToPricing}
              >
                <ShoppingCart className="w-5 h-5 mr-2" />
                View Pricing Options
              </Button>
            </CardContent>
          </Card>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/50 py-8 mt-12">
        <div className="container mx-auto px-4 text-center text-slate-500 text-sm">
          © 2025 ActorHub.ai. All rights reserved.
        </div>
      </footer>

      {/* Modals */}
      <ShareModal isOpen={showShareModal} onClose={() => setShowShareModal(false)} actor={actor} />
      <ContactModal isOpen={showContactModal} onClose={() => setShowContactModal(false)} actor={actor} />
      <PreviewModal isOpen={showPreviewModal} onClose={() => setShowPreviewModal(false)} actor={actor} />
    </div>
  )
}

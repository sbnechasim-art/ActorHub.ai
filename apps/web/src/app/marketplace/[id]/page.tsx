'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import {
  Shield, Star, CheckCircle, Play, Download, Share2,
  Heart, Eye, Award,
  Mic, Video, ImageIcon, Globe, DollarSign,
  ShoppingCart, Zap, MessageSquare, ArrowLeft
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CartButton } from '@/components/cart'
import { useCartStore } from '@/store/cart'
import { marketplaceApi } from '@/lib/api'
import { formatCurrency, cn } from '@/lib/utils'

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
  'actor-1': {
    id: 'actor-1',
    title: 'Alex Turner',
    short_description: 'Young actor with fresh energy. Perfect for youth-oriented content.',
    description: 'Alex Turner is a rising young actor bringing fresh energy and authenticity to every role. Perfect for youth-oriented content, social media campaigns, and modern storytelling. His natural charisma makes him ideal for brands targeting younger demographics.',
    thumbnail_url: 'https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=800&h=800&fit=crop&crop=face',
    gallery: [
      'https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=600&h=400&fit=crop',
    ],
    category: 'actor',
    avg_rating: 4.6,
    rating_count: 42,
    license_count: 28,
    view_count: 3421,
    pricing_tiers: [
      { name: 'Basic', price: 149, features: ['10 AI generations', 'Personal use only', '30 day license'] },
      { name: 'Pro', price: 349, features: ['100 AI generations', 'Commercial use', '90 day license'] },
    ],
    tags: ['Youth', 'Commercial', 'Social'],
    verified: true,
    languages: ['English'],
    available_components: ['Face'],
  },
  'actor-2': {
    id: 'actor-2',
    title: 'Isabella Martinez',
    short_description: 'Bilingual actress fluent in English and Spanish. Diverse range.',
    description: 'Isabella Martinez is a talented bilingual actress fluent in both English and Spanish. Her diverse range allows her to seamlessly transition between cultures and character types. Perfect for multicultural campaigns and international productions.',
    thumbnail_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&h=800&fit=crop&crop=face',
    gallery: [
      'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=600&h=400&fit=crop',
    ],
    category: 'actor',
    avg_rating: 4.8,
    rating_count: 76,
    license_count: 54,
    view_count: 6789,
    pricing_tiers: [
      { name: 'Basic', price: 249, features: ['10 AI generations', 'Personal use only', '30 day license'] },
      { name: 'Pro', price: 549, features: ['100 AI generations', 'Commercial use', 'Voice included', '90 day license'] },
    ],
    tags: ['Bilingual', 'Commercial', 'Film'],
    verified: true,
    languages: ['English', 'Spanish'],
    available_components: ['Face', 'Voice'],
  },
  'actor-3': {
    id: 'actor-3',
    title: 'David Kim',
    short_description: 'Action specialist with martial arts background. Stunt coordination.',
    description: 'David Kim is an action specialist with an extensive martial arts background and stunt coordination experience. His dynamic physicality and precision make him perfect for action sequences, sports content, and high-energy productions.',
    thumbnail_url: 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=800&h=800&fit=crop&crop=face',
    gallery: [
      'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=600&h=400&fit=crop',
    ],
    category: 'actor',
    avg_rating: 4.9,
    rating_count: 89,
    license_count: 67,
    view_count: 8234,
    pricing_tiers: [
      { name: 'Basic', price: 399, features: ['10 AI generations', 'Personal use only', '30 day license'] },
      { name: 'Pro', price: 799, features: ['100 AI generations', 'Commercial use', 'Motion included', '90 day license'] },
    ],
    tags: ['Action', 'Stunts', 'Film', 'Sports'],
    verified: true,
    languages: ['English', 'Korean'],
    available_components: ['Face', 'Motion'],
  },
  'model-1': {
    id: 'model-1',
    title: 'Sophie Anderson',
    short_description: 'High fashion model with runway experience. Editorial specialist.',
    description: 'Sophie Anderson is a high fashion model with extensive runway and editorial experience. Her elegant presence and versatility make her perfect for luxury brands, fashion campaigns, and lifestyle content.',
    thumbnail_url: 'https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=800&h=800&fit=crop&crop=face',
    gallery: [
      'https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=600&h=400&fit=crop',
    ],
    category: 'model',
    avg_rating: 4.7,
    rating_count: 112,
    license_count: 198,
    view_count: 14532,
    pricing_tiers: [
      { name: 'Basic', price: 279, features: ['10 AI generations', 'Personal use only', '30 day license'] },
      { name: 'Pro', price: 579, features: ['100 AI generations', 'Commercial use', '90 day license'] },
    ],
    tags: ['Fashion', 'Editorial', 'Runway', 'Luxury'],
    verified: true,
    languages: ['English'],
    available_components: ['Face'],
  },
  'model-2': {
    id: 'model-2',
    title: 'Marcus Johnson',
    short_description: 'Fitness model and brand ambassador. Athletic builds specialist.',
    description: 'Marcus Johnson is a fitness model and brand ambassador specializing in athletic and sports content. His dedication to fitness and natural athleticism make him ideal for sports brands, health campaigns, and lifestyle content.',
    thumbnail_url: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=800&h=800&fit=crop&crop=face',
    gallery: [
      'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=600&h=400&fit=crop',
    ],
    category: 'model',
    avg_rating: 4.5,
    rating_count: 58,
    license_count: 82,
    view_count: 5678,
    pricing_tiers: [
      { name: 'Basic', price: 199, features: ['10 AI generations', 'Personal use only', '30 day license'] },
      { name: 'Pro', price: 449, features: ['100 AI generations', 'Commercial use', '90 day license'] },
    ],
    tags: ['Fitness', 'Sports', 'Commercial', 'Health'],
    verified: true,
    languages: ['English'],
    available_components: ['Face', 'Motion'],
  },
  'voice-1': {
    id: 'voice-1',
    title: 'Rachel Green',
    short_description: 'Professional voice actress with 500+ projects. Animation expert.',
    description: 'Rachel Green is a professional voice actress with over 500 completed projects spanning animation, video games, and audiobooks. Her range and emotional depth make her perfect for character work and narrative content.',
    thumbnail_url: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=800&h=800&fit=crop&crop=face',
    gallery: [
      'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=600&h=400&fit=crop',
    ],
    category: 'voice',
    avg_rating: 4.9,
    rating_count: 234,
    license_count: 421,
    view_count: 22341,
    pricing_tiers: [
      { name: 'Basic', price: 179, features: ['5 minutes of audio', 'Personal use only'] },
      { name: 'Pro', price: 449, features: ['30 minutes of audio', 'Commercial use', 'Multiple emotions'] },
    ],
    tags: ['Animation', 'Games', 'Audiobook', 'Character'],
    verified: true,
    languages: ['English'],
    available_components: ['Voice'],
  },
  'influencer-1': {
    id: 'influencer-1',
    title: 'Tyler Brooks',
    short_description: 'Social media personality with 2M+ followers. Gen-Z specialist.',
    description: 'Tyler Brooks is a social media personality with over 2 million followers across platforms. His authentic connection with Gen-Z audiences makes him perfect for brands targeting younger demographics.',
    thumbnail_url: 'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=800&h=800&fit=crop&crop=face',
    gallery: [
      'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=600&h=400&fit=crop',
    ],
    category: 'influencer',
    avg_rating: 4.4,
    rating_count: 167,
    license_count: 289,
    view_count: 19823,
    pricing_tiers: [
      { name: 'Basic', price: 129, features: ['10 AI generations', 'Personal use only', '30 day license'] },
      { name: 'Pro', price: 329, features: ['100 AI generations', 'Commercial use', '90 day license'] },
    ],
    tags: ['Social', 'Youth', 'Lifestyle', 'Trending'],
    verified: true,
    languages: ['English'],
    available_components: ['Face'],
  },
  'influencer-2': {
    id: 'influencer-2',
    title: 'Olivia Park',
    short_description: 'Beauty and lifestyle creator. Brand collaboration expert.',
    description: 'Olivia Park is a beauty and lifestyle creator known for her stunning visuals and engaging content. Her expertise in brand collaborations makes her perfect for beauty, fashion, and lifestyle campaigns.',
    thumbnail_url: 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=800&h=800&fit=crop&crop=face',
    gallery: [
      'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=600&h=400&fit=crop',
    ],
    category: 'influencer',
    avg_rating: 4.6,
    rating_count: 145,
    license_count: 203,
    view_count: 16432,
    pricing_tiers: [
      { name: 'Basic', price: 159, features: ['10 AI generations', 'Personal use only', '30 day license'] },
      { name: 'Pro', price: 379, features: ['100 AI generations', 'Commercial use', '90 day license'] },
    ],
    tags: ['Beauty', 'Lifestyle', 'Fashion', 'Brand'],
    verified: true,
    languages: ['English', 'Korean'],
    available_components: ['Face'],
  },
}

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

export default function ActorDetailPage() {
  const params = useParams()
  const id = params.id as string
  const [selectedImage, setSelectedImage] = useState(0)
  const [isLiked, setIsLiked] = useState(false)

  // Try to get from API first, fallback to sample data
  const { data: apiActor, isLoading } = useQuery({
    queryKey: ['listing', id],
    queryFn: () => marketplaceApi.getListing(id),
    retry: false,
  })

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

  const gallery = actor.gallery || [actor.thumbnail_url]

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
            <Button variant="ghost" size="icon" onClick={() => setIsLiked(!isLiked)}>
              <Heart className={cn("w-5 h-5", isLiked ? "fill-red-500 text-red-500" : "text-slate-400")} />
            </Button>
            <Button variant="ghost" size="icon">
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
              <Button size="lg" className="flex-1 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700">
                <Play className="w-5 h-5 mr-2" />
                Preview Demo
              </Button>
              <Button size="lg" variant="outline" className="border-slate-700">
                <MessageSquare className="w-5 h-5 mr-2" />
                Contact
              </Button>
            </div>
          </div>
        </div>

        {/* Pricing Section */}
        <section className="mb-12">
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
              <Button size="lg" className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700">
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
    </div>
  )
}

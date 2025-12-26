'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation } from '@tanstack/react-query'
import Link from 'next/link'
import {
  Shield, ArrowLeft, Mic, Video, ImageIcon, Upload, Play,
  CheckCircle, AlertCircle, Loader2, Sparkles, Clock
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { marketplaceApi, generationApi, GenerationResponse } from '@/lib/api'
import { cn, getProxiedImageUrl } from '@/lib/utils'

type ContentType = 'face' | 'voice' | 'motion'

interface License {
  id: string
  identity_id: string
  identity: {
    display_name: string
    profile_image_url: string
  }
  license_type: string
  usage_type: string
  valid_until: string
  is_active: boolean
}

export default function CreateContentPage() {
  const router = useRouter()
  const [selectedLicense, setSelectedLicense] = useState<string | null>(null)
  const [contentType, setContentType] = useState<ContentType>('face')
  const [prompt, setPrompt] = useState('')
  const [file, setFile] = useState<File | null>(null)

  // Fetch user's active licenses
  const { data: licenses, isLoading: licensesLoading } = useQuery({
    queryKey: ['my-licenses'],
    queryFn: () => marketplaceApi.getMyLicenses(),
  })

  // Submit generation request - Real API
  const generateMutation = useMutation({
    mutationFn: async (): Promise<GenerationResponse> => {
      return generationApi.generate({
        license_id: selectedLicense!,
        content_type: contentType,
        prompt: prompt,
        num_outputs: contentType === 'face' ? 2 : 1,
      })
    },
    onSuccess: (data: GenerationResponse) => {
      router.push(`/gallery?job=${data.job_id}`)
    }
  })

  const activeLicenses = licenses?.filter((l: License) => l.is_active) || []

  const contentTypes = [
    { id: 'face', label: 'Face Generation', icon: ImageIcon, description: 'Generate images with the actor\'s face' },
    { id: 'voice', label: 'Voice Synthesis', icon: Mic, description: 'Generate speech with the actor\'s voice' },
    { id: 'motion', label: 'Motion Capture', icon: Video, description: 'Apply motion to the actor\'s model' }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-xl">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-2 text-slate-400 hover:text-white transition">
            <ArrowLeft className="w-5 h-5" />
            <span>Back to Dashboard</span>
          </Link>
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-white">ActorHub.ai</span>
          </Link>
          <div className="w-24" />
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Page Title */}
          <div className="text-center mb-12">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-white mb-2">Create AI Content</h1>
            <p className="text-slate-400">
              Generate content using your licensed actor packs
            </p>
          </div>

          {/* Step 1: Select License */}
          <Card className="bg-slate-800/50 border-slate-700 mb-8">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-blue-500 text-white text-sm flex items-center justify-center">1</span>
                Select Licensed Actor
              </CardTitle>
            </CardHeader>
            <CardContent>
              {licensesLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-6 h-6 text-purple-500 animate-spin" />
                </div>
              ) : activeLicenses.length === 0 ? (
                <div className="text-center py-8">
                  <AlertCircle className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-white mb-2">No Active Licenses</h3>
                  <p className="text-slate-400 mb-4">
                    Purchase a license from the marketplace to start creating content.
                  </p>
                  <Button asChild className="bg-purple-600 hover:bg-purple-700">
                    <Link href="/marketplace">
                      Browse Marketplace
                    </Link>
                  </Button>
                </div>
              ) : (
                <div className="grid md:grid-cols-2 gap-4">
                  {activeLicenses.map((license: License) => (
                    <button
                      key={license.id}
                      onClick={() => setSelectedLicense(license.id)}
                      className={cn(
                        'flex items-center gap-4 p-4 rounded-lg border transition-all text-left',
                        selectedLicense === license.id
                          ? 'border-purple-500 bg-purple-500/10'
                          : 'border-slate-700 hover:border-slate-600'
                      )}
                    >
                      <div className="w-14 h-14 rounded-lg overflow-hidden bg-slate-700 flex-shrink-0">
                        {getProxiedImageUrl(license.identity?.profile_image_url) ? (
                          <img
                            src={getProxiedImageUrl(license.identity?.profile_image_url)}
                            alt={license.identity?.display_name}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <Shield className="w-6 h-6 text-slate-500" />
                          </div>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="font-medium text-white truncate">
                          {license.identity?.display_name || 'Unknown Actor'}
                        </h4>
                        <p className="text-sm text-slate-400 capitalize">
                          {license.license_type} License
                        </p>
                        <div className="flex items-center gap-1 text-xs text-green-400 mt-1">
                          <Clock className="w-3 h-3" />
                          Valid until {new Date(license.valid_until).toLocaleDateString()}
                        </div>
                      </div>
                      {selectedLicense === license.id && (
                        <CheckCircle className="w-5 h-5 text-purple-400 flex-shrink-0" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Step 2: Content Type */}
          <Card className={cn(
            'bg-slate-800/50 border-slate-700 mb-8 transition-opacity',
            !selectedLicense && 'opacity-50 pointer-events-none'
          )}>
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-blue-500 text-white text-sm flex items-center justify-center">2</span>
                Select Content Type
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-4">
                {contentTypes.map((type) => (
                  <button
                    key={type.id}
                    onClick={() => setContentType(type.id as ContentType)}
                    className={cn(
                      'p-6 rounded-lg border text-center transition-all',
                      contentType === type.id
                        ? 'border-purple-500 bg-purple-500/10'
                        : 'border-slate-700 hover:border-slate-600'
                    )}
                  >
                    <type.icon className={cn(
                      'w-8 h-8 mx-auto mb-3',
                      contentType === type.id ? 'text-purple-400' : 'text-slate-500'
                    )} />
                    <h4 className="font-medium text-white mb-1">{type.label}</h4>
                    <p className="text-xs text-slate-400">{type.description}</p>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Step 3: Input */}
          <Card className={cn(
            'bg-slate-800/50 border-slate-700 mb-8 transition-opacity',
            !selectedLicense && 'opacity-50 pointer-events-none'
          )}>
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-blue-500 text-white text-sm flex items-center justify-center">3</span>
                Provide Input
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {contentType === 'voice' ? (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Text to Speak
                  </label>
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Enter the text you want the actor to speak..."
                    className="w-full h-32 px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                  <p className="text-xs text-slate-500 mt-2">
                    Maximum 500 characters. Emotion tags like [happy], [sad], [excited] are supported.
                  </p>
                </div>
              ) : contentType === 'face' ? (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Image Prompt
                  </label>
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Describe the image you want to generate (e.g., 'professional headshot, smiling, blue background')..."
                    className="w-full h-32 px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Reference Video
                  </label>
                  <div className="border-2 border-dashed border-slate-700 rounded-lg p-8 text-center">
                    <input
                      type="file"
                      accept="video/*"
                      onChange={(e) => setFile(e.target.files?.[0] || null)}
                      className="hidden"
                      id="video-upload"
                    />
                    <label htmlFor="video-upload" className="cursor-pointer">
                      {file ? (
                        <div className="flex flex-col items-center">
                          <Video className="w-12 h-12 text-green-400 mb-2" />
                          <p className="text-green-400">{file.name}</p>
                          <p className="text-xs text-slate-500 mt-1">Click to change</p>
                        </div>
                      ) : (
                        <div className="flex flex-col items-center">
                          <Upload className="w-12 h-12 text-slate-500 mb-2" />
                          <p className="text-slate-400">Upload reference video</p>
                          <p className="text-xs text-slate-500 mt-1">MP4, MOV up to 100MB</p>
                        </div>
                      )}
                    </label>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Generate Button */}
          <div className="flex justify-center">
            <Button
              onClick={() => generateMutation.mutate()}
              disabled={!selectedLicense || !prompt || generateMutation.isPending}
              className="px-12 py-6 text-lg bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700"
            >
              {generateMutation.isPending ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Play className="w-5 h-5 mr-2" />
                  Generate Content
                </>
              )}
            </Button>
          </div>

          {/* Info */}
          <p className="text-center text-slate-500 text-sm mt-8">
            Generation typically takes 2-5 minutes. You'll be notified when it's ready.
          </p>
        </div>
      </main>
    </div>
  )
}

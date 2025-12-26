'use client'

import { useState, useCallback } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import Link from 'next/link'
import {
  ArrowLeft, Upload, X, Image as ImageIcon, Mic, Play,
  CheckCircle, AlertCircle, Loader2, Sparkles, Info
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { identityApi, actorPackApi } from '@/lib/api'
import { cn } from '@/lib/utils'

const MIN_IMAGES = 8
const MAX_IMAGES = 30
const MAX_AUDIO_FILES = 5

export default function TrainActorPackPage() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const queryClient = useQueryClient()
  const identityId = params.id as string
  const isRetrain = searchParams.get('retrain') === 'true'

  // State
  const [trainingImages, setTrainingImages] = useState<File[]>([])
  const [audioFiles, setAudioFiles] = useState<File[]>([])
  const [previews, setPreviews] = useState<string[]>([])

  // Fetch identity details
  const { data: identity, isLoading: identityLoading } = useQuery({
    queryKey: ['identity', identityId],
    queryFn: () => identityApi.getIdentity(identityId),
    enabled: !!identityId,
  })

  // Image dropzone
  const onDropImages = useCallback((acceptedFiles: File[]) => {
    const newFiles = [...trainingImages, ...acceptedFiles].slice(0, MAX_IMAGES)
    setTrainingImages(newFiles)

    // Create previews
    const newPreviews = newFiles.map(file => URL.createObjectURL(file))
    setPreviews(prev => {
      prev.forEach(url => URL.revokeObjectURL(url))
      return newPreviews
    })
  }, [trainingImages])

  const imageDropzone = useDropzone({
    onDrop: onDropImages,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png'] },
    maxSize: 10 * 1024 * 1024, // 10MB per file
    multiple: true, // Allow selecting multiple files at once
  })

  // Audio dropzone
  const onDropAudio = useCallback((acceptedFiles: File[]) => {
    const newFiles = [...audioFiles, ...acceptedFiles].slice(0, MAX_AUDIO_FILES)
    setAudioFiles(newFiles)
  }, [audioFiles])

  const audioDropzone = useDropzone({
    onDrop: onDropAudio,
    accept: { 'audio/*': ['.mp3', '.wav', '.m4a', '.ogg'] },
    maxSize: 50 * 1024 * 1024, // 50MB per file
    multiple: true, // Allow selecting multiple files at once
  })

  // Remove image
  const removeImage = (index: number) => {
    setTrainingImages(prev => prev.filter((_, i) => i !== index))
    setPreviews(prev => {
      URL.revokeObjectURL(prev[index])
      return prev.filter((_, i) => i !== index)
    })
  }

  // Remove audio
  const removeAudio = (index: number) => {
    setAudioFiles(prev => prev.filter((_, i) => i !== index))
  }

  // Start training mutation
  const trainMutation = useMutation({
    mutationFn: async () => {
      const formData = new FormData()

      // Pack data as JSON string
      formData.append('pack_data', JSON.stringify({
        name: identity?.display_name || identity?.name,
        description: `AI Actor Pack for ${identity?.display_name || identity?.name}`,
      }))

      // Add training images
      trainingImages.forEach(img => {
        formData.append('training_images', img)
      })

      // Add audio files if any
      audioFiles.forEach(audio => {
        formData.append('training_audio', audio)
      })

      // Add retrain flag if retraining
      if (isRetrain) {
        formData.append('retrain', 'true')
      }

      return actorPackApi.initTraining(formData)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['identity', identityId] })
      router.push(`/identity/${identityId}`)
    },
  })

  const canStartTraining = trainingImages.length >= MIN_IMAGES

  if (identityLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
      </div>
    )
  }

  if (!identity) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <Card className="bg-slate-800 border-slate-700 max-w-md">
          <CardContent className="p-8 text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Identity Not Found</h2>
            <p className="text-slate-400 mb-4">The identity you're looking for doesn't exist.</p>
            <Button asChild>
              <Link href="/dashboard">Go to Dashboard</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Check if already has actor pack (block unless retrain mode)
  if (identity.actor_pack && !isRetrain) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <Card className="bg-slate-800 border-slate-700 max-w-md">
          <CardContent className="p-8 text-center">
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Actor Pack Already Exists</h2>
            <p className="text-slate-400 mb-4">
              This identity already has an Actor Pack.
              Status: <span className="text-purple-400">{identity.actor_pack.training_status}</span>
            </p>
            <div className="flex gap-3 justify-center">
              <Button asChild variant="outline">
                <Link href={`/identity/${identityId}`}>View Identity</Link>
              </Button>
              <Button asChild>
                <Link href={`/identity/${identityId}/train?retrain=true`}>Retrain</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-xl">
        <div className="container mx-auto px-4 h-16 flex items-center">
          <Link
            href={`/identity/${identityId}`}
            className="flex items-center gap-2 text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>Back to Identity</span>
          </Link>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Title */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center mx-auto mb-4">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">
            {isRetrain ? 'Retrain Actor Pack' : 'Train Actor Pack'}
          </h1>
          <p className="text-slate-400">
            {isRetrain ? (
              <>Upload new training data for <span className="text-purple-400">{identity.display_name}</span></>
            ) : (
              <>Upload training data for <span className="text-purple-400">{identity.display_name}</span></>
            )}
          </p>
          {isRetrain && (
            <p className="text-amber-400 text-sm mt-2">
              This will replace the existing Actor Pack with a new one
            </p>
          )}
        </div>

        {/* Info Card */}
        <Card className="bg-blue-500/10 border-blue-500/30 mb-8">
          <CardContent className="p-4 flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-blue-100">
              <p className="font-medium mb-1">Training Requirements</p>
              <ul className="list-disc list-inside space-y-1 text-blue-200">
                <li>Minimum {MIN_IMAGES} high-quality face images from different angles</li>
                <li>Good lighting, clear face visibility, no sunglasses</li>
                <li>Variety of expressions (neutral, smiling, serious)</li>
                <li>Optional: Audio samples (30+ seconds) for voice cloning</li>
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Step 1: Images */}
        <Card className="bg-slate-800/50 border-slate-700 mb-6">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-blue-500 text-white text-sm flex items-center justify-center">1</span>
              Upload Training Images
              <span className="text-sm font-normal text-slate-400 ml-2">
                ({trainingImages.length}/{MIN_IMAGES} minimum)
              </span>
            </CardTitle>
            <CardDescription>
              Upload {MIN_IMAGES}-{MAX_IMAGES} high-quality face photos from different angles
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* Dropzone */}
            <div
              {...imageDropzone.getRootProps()}
              className={cn(
                'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
                imageDropzone.isDragActive
                  ? 'border-purple-500 bg-purple-500/10'
                  : 'border-slate-600 hover:border-slate-500'
              )}
            >
              <input {...imageDropzone.getInputProps()} multiple />
              <Upload className="w-10 h-10 text-slate-500 mx-auto mb-3" />
              <p className="text-slate-300">
                Drag & drop images here, or click to select multiple
              </p>
              <p className="text-sm text-slate-500 mt-1">
                JPG, PNG up to 10MB each • Select all {MIN_IMAGES}-{MAX_IMAGES} images at once
              </p>
            </div>

            {/* Image Previews */}
            {previews.length > 0 && (
              <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-3 mt-6">
                {previews.map((preview, index) => (
                  <div key={index} className="relative group">
                    <img
                      src={preview}
                      alt={`Training ${index + 1}`}
                      className="w-full aspect-square object-cover rounded-lg"
                    />
                    <button
                      onClick={() => removeImage(index)}
                      className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="w-4 h-4 text-white" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Progress indicator */}
            <div className="mt-4">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-400">Upload Progress</span>
                <span className={trainingImages.length >= MIN_IMAGES ? 'text-green-400' : 'text-slate-400'}>
                  {trainingImages.length} / {MIN_IMAGES} minimum
                </span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-2">
                <div
                  className={cn(
                    'h-2 rounded-full transition-all',
                    trainingImages.length >= MIN_IMAGES ? 'bg-green-500' : 'bg-blue-500'
                  )}
                  style={{ width: `${Math.min((trainingImages.length / MIN_IMAGES) * 100, 100)}%` }}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Step 2: Audio (Optional) */}
        <Card className="bg-slate-800/50 border-slate-700 mb-8">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-slate-600 text-white text-sm flex items-center justify-center">2</span>
              Upload Voice Samples
              <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded ml-2">Optional</span>
            </CardTitle>
            <CardDescription>
              Upload audio samples for voice cloning (30+ seconds recommended)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              {...audioDropzone.getRootProps()}
              className={cn(
                'border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors',
                audioDropzone.isDragActive
                  ? 'border-purple-500 bg-purple-500/10'
                  : 'border-slate-600 hover:border-slate-500'
              )}
            >
              <input {...audioDropzone.getInputProps()} multiple />
              <Mic className="w-8 h-8 text-slate-500 mx-auto mb-2" />
              <p className="text-slate-300 text-sm">
                Drag & drop audio files, or click to select multiple
              </p>
              <p className="text-xs text-slate-500 mt-1">
                MP3, WAV, M4A up to 50MB each • Select multiple files at once
              </p>
            </div>

            {/* Audio Files List */}
            {audioFiles.length > 0 && (
              <div className="space-y-2 mt-4">
                {audioFiles.map((file, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <Mic className="w-5 h-5 text-purple-400" />
                      <div>
                        <p className="text-white text-sm">{file.name}</p>
                        <p className="text-xs text-slate-500">
                          {(file.size / (1024 * 1024)).toFixed(2)} MB
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => removeAudio(index)}
                      className="text-slate-400 hover:text-red-400 transition"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Start Training Button */}
        <div className="flex flex-col items-center gap-4">
          <Button
            onClick={() => trainMutation.mutate()}
            disabled={!canStartTraining || trainMutation.isPending}
            className="px-12 py-6 text-lg bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:opacity-50"
          >
            {trainMutation.isPending ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                {isRetrain ? 'Starting Retrain...' : 'Starting Training...'}
              </>
            ) : (
              <>
                <Play className="w-5 h-5 mr-2" />
                {isRetrain ? 'Start Retrain' : 'Start Training'}
              </>
            )}
          </Button>

          {!canStartTraining && (
            <p className="text-amber-400 text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              Upload at least {MIN_IMAGES} images to start training
            </p>
          )}

          {trainMutation.isError && (
            <p className="text-red-400 text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              {(trainMutation.error as any)?.response?.data?.detail || 'Training failed. Please try again.'}
            </p>
          )}

          <p className="text-slate-500 text-sm text-center max-w-md">
            Training typically takes 15-30 minutes. You'll receive a notification when it's complete.
          </p>
        </div>
      </main>
    </div>
  )
}

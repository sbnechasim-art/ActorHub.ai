'use client'

import { useState, useCallback, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import Link from 'next/link'
import {
  ArrowLeft,
  Save,
  Loader2,
  Upload,
  X,
  Image as ImageIcon,
  Eye,
  EyeOff,
  DollarSign,
  AlertCircle,
  CheckCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { identityApi, Identity } from '@/lib/api'
import { cn } from '@/lib/utils'

interface FormData {
  display_name: string
  bio: string
  category: string
  is_public: boolean
  pricing: {
    personal: number
    commercial: number
    enterprise: number
  }
}

interface FormErrors {
  display_name?: string
  bio?: string
  category?: string
  pricing?: string
}

const CATEGORY_OPTIONS = [
  { value: '', label: 'Select a category' },
  { value: 'actor', label: 'Actor / Performer' },
  { value: 'musician', label: 'Musician / Artist' },
  { value: 'influencer', label: 'Social Media Influencer' },
  { value: 'athlete', label: 'Athlete' },
  { value: 'business', label: 'Business Professional' },
  { value: 'creator', label: 'Content Creator' },
  { value: 'other', label: 'Other' },
]

export default function IdentityEditPage() {
  const params = useParams()
  const router = useRouter()
  const queryClient = useQueryClient()
  const identityId = params.id as string

  // Notification state
  const [notification, setNotification] = useState<{
    type: 'success' | 'error'
    message: string
  } | null>(null)

  // Form state
  const [formData, setFormData] = useState<FormData>({
    display_name: '',
    bio: '',
    category: '',
    is_public: false,
    pricing: {
      personal: 0,
      commercial: 0,
      enterprise: 0,
    },
  })
  const [formErrors, setFormErrors] = useState<FormErrors>({})
  const [additionalImages, setAdditionalImages] = useState<File[]>([])
  const [imagePreviews, setImagePreviews] = useState<string[]>([])

  // Fetch identity data
  const {
    data: identity,
    isLoading,
    error,
  } = useQuery<Identity>({
    queryKey: ['identity', identityId],
    queryFn: () => identityApi.getIdentity(identityId),
    enabled: !!identityId,
  })

  // Populate form when identity loads
  useEffect(() => {
    if (identity) {
      setFormData({
        display_name: identity.display_name || identity.name || '',
        bio: identity.bio || '',
        category: identity.category || '',
        is_public: identity.is_public ?? false,
        pricing: {
          personal: 0,
          commercial: 0,
          enterprise: 0,
        },
      })
    }
  }, [identity])

  // Clean up image previews on unmount
  useEffect(() => {
    return () => {
      imagePreviews.forEach((url) => URL.revokeObjectURL(url))
    }
  }, [imagePreviews])

  // Auto-hide notification
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [notification])

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: async (data: Partial<FormData>) => {
      return identityApi.update(identityId, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['identity', identityId] })
      setNotification({
        type: 'success',
        message: 'Identity updated successfully!',
      })
    },
    onError: (error: any) => {
      let errorMessage = 'Failed to update identity'
      const detail = error.response?.data?.detail
      if (typeof detail === 'string') {
        errorMessage = detail
      } else if (Array.isArray(detail) && detail.length > 0) {
        errorMessage = detail.map((d: any) => d.msg || d.message || JSON.stringify(d)).join(', ')
      }
      setNotification({
        type: 'error',
        message: errorMessage,
      })
    },
  })

  // Image dropzone
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const newFiles = acceptedFiles.slice(0, 5 - additionalImages.length)
      setAdditionalImages((prev) => [...prev, ...newFiles])

      const newPreviews = newFiles.map((file) => URL.createObjectURL(file))
      setImagePreviews((prev) => [...prev, ...newPreviews])
    },
    [additionalImages.length]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png'] },
    maxFiles: 5,
    maxSize: 10 * 1024 * 1024,
    disabled: additionalImages.length >= 5,
  })

  const removeImage = (index: number) => {
    URL.revokeObjectURL(imagePreviews[index])
    setAdditionalImages((prev) => prev.filter((_, i) => i !== index))
    setImagePreviews((prev) => prev.filter((_, i) => i !== index))
  }

  // Form validation
  const validateForm = (): boolean => {
    const errors: FormErrors = {}

    if (!formData.display_name.trim()) {
      errors.display_name = 'Display name is required'
    } else if (formData.display_name.length < 2) {
      errors.display_name = 'Display name must be at least 2 characters'
    } else if (formData.display_name.length > 100) {
      errors.display_name = 'Display name must be less than 100 characters'
    }

    if (formData.bio && formData.bio.length > 1000) {
      errors.bio = 'Bio must be less than 1000 characters'
    }

    if (formData.pricing.personal < 0 || formData.pricing.commercial < 0 || formData.pricing.enterprise < 0) {
      errors.pricing = 'Pricing cannot be negative'
    }

    setFormErrors(errors)
    return Object.keys(errors).length === 0
  }

  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      setNotification({
        type: 'error',
        message: 'Please fix the form errors before saving',
      })
      return
    }

    updateMutation.mutate({
      display_name: formData.display_name,
      bio: formData.bio,
      category: formData.category,
      is_public: formData.is_public,
    })
  }

  // Handle field changes
  const handleChange = (field: keyof FormData, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    // Clear error when user starts typing
    if (formErrors[field as keyof FormErrors]) {
      setFormErrors((prev) => ({ ...prev, [field]: undefined }))
    }
  }

  const handlePricingChange = (tier: 'personal' | 'commercial' | 'enterprise', value: string) => {
    const numValue = parseFloat(value) || 0
    setFormData((prev) => ({
      ...prev,
      pricing: { ...prev.pricing, [tier]: numValue },
    }))
    if (formErrors.pricing) {
      setFormErrors((prev) => ({ ...prev, pricing: undefined }))
    }
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
        <header className="border-b border-slate-800">
          <div className="container mx-auto px-4 h-16 flex items-center">
            <div className="h-6 w-32 bg-slate-800 rounded animate-pulse" />
          </div>
        </header>
        <main className="container mx-auto px-4 py-8 max-w-3xl">
          <div className="space-y-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-48 bg-slate-800/50 rounded-xl animate-pulse" />
            ))}
          </div>
        </main>
      </div>
    )
  }

  // Error state
  if (error || !identity) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <Card className="bg-slate-800/50 border-slate-700 max-w-md">
          <CardContent className="p-8 text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Identity Not Found</h2>
            <p className="text-slate-400 mb-6">
              The identity you're trying to edit doesn't exist or you don't have permission to edit it.
            </p>
            <Button variant="outline" asChild>
              <Link href="/dashboard">Back to Dashboard</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* Notification */}
      {notification && (
        <div
          className={cn(
            'fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg flex items-center gap-3 animate-in slide-in-from-top-2',
            notification.type === 'success'
              ? 'bg-green-500 text-white'
              : 'bg-red-500 text-white'
          )}
        >
          {notification.type === 'success' ? (
            <CheckCircle className="w-5 h-5" />
          ) : (
            <AlertCircle className="w-5 h-5" />
          )}
          <span>{notification.message}</span>
          <button
            onClick={() => setNotification(null)}
            className="ml-2 hover:opacity-80"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Header */}
      <header className="border-b border-slate-800">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link
            href={`/identity/${identityId}`}
            className="flex items-center gap-2 text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Identity
          </Link>
          <Button
            onClick={handleSubmit}
            disabled={updateMutation.isPending}
            variant="gradient"
          >
            {updateMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Save Changes
              </>
            )}
          </Button>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-3xl">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Information */}
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Basic Information</CardTitle>
              <CardDescription>Update your identity's public profile</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Display Name */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Display Name <span className="text-red-500">*</span>
                </label>
                <Input
                  value={formData.display_name}
                  onChange={(e) => handleChange('display_name', e.target.value)}
                  placeholder="How you want to be identified"
                  className={cn(
                    'bg-slate-900 border-slate-700',
                    formErrors.display_name && 'border-red-500'
                  )}
                />
                {formErrors.display_name && (
                  <p className="text-red-500 text-sm mt-1">{formErrors.display_name}</p>
                )}
                <p className="text-slate-500 text-sm mt-1">
                  {formData.display_name.length}/100 characters
                </p>
              </div>

              {/* Bio */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Bio
                </label>
                <textarea
                  value={formData.bio}
                  onChange={(e) => handleChange('bio', e.target.value)}
                  placeholder="Tell people about yourself..."
                  rows={4}
                  className={cn(
                    'flex w-full rounded-md border bg-slate-900 border-slate-700 px-3 py-2 text-sm placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50',
                    formErrors.bio && 'border-red-500'
                  )}
                />
                {formErrors.bio && (
                  <p className="text-red-500 text-sm mt-1">{formErrors.bio}</p>
                )}
                <p className="text-slate-500 text-sm mt-1">
                  {formData.bio.length}/1000 characters
                </p>
              </div>

              {/* Category */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Category
                </label>
                <select
                  value={formData.category}
                  onChange={(e) => handleChange('category', e.target.value)}
                  className="flex h-10 w-full rounded-md border bg-slate-900 border-slate-700 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                >
                  {CATEGORY_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </CardContent>
          </Card>

          {/* Privacy Settings */}
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Privacy Settings</CardTitle>
              <CardDescription>Control who can see your identity</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between p-4 rounded-lg bg-slate-900/50">
                <div className="flex items-center gap-3">
                  {formData.is_public ? (
                    <Eye className="w-5 h-5 text-green-500" />
                  ) : (
                    <EyeOff className="w-5 h-5 text-slate-500" />
                  )}
                  <div>
                    <p className="font-medium text-white">Public Profile</p>
                    <p className="text-sm text-slate-400">
                      {formData.is_public
                        ? 'Your identity is visible in the marketplace'
                        : 'Your identity is hidden from the marketplace'}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleChange('is_public', !formData.is_public)}
                  className={cn(
                    'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                    formData.is_public ? 'bg-green-500' : 'bg-slate-700'
                  )}
                >
                  <span
                    className={cn(
                      'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                      formData.is_public ? 'translate-x-6' : 'translate-x-1'
                    )}
                  />
                </button>
              </div>
            </CardContent>
          </Card>

          {/* Additional Images */}
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Additional Images</CardTitle>
              <CardDescription>
                Upload more photos for better AI training (max 5 images)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Image Previews */}
              {imagePreviews.length > 0 && (
                <div className="grid grid-cols-5 gap-3">
                  {imagePreviews.map((preview, index) => (
                    <div key={index} className="relative aspect-square">
                      <img
                        src={preview}
                        alt={`Upload ${index + 1}`}
                        className="w-full h-full object-cover rounded-lg"
                      />
                      <button
                        type="button"
                        onClick={() => removeImage(index)}
                        className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Dropzone */}
              {additionalImages.length < 5 && (
                <div
                  {...getRootProps()}
                  className={cn(
                    'border-2 border-dashed rounded-xl p-8 cursor-pointer transition-colors text-center',
                    isDragActive
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-slate-700 hover:border-slate-600'
                  )}
                >
                  <input {...getInputProps()} />
                  <ImageIcon className="w-10 h-10 text-slate-500 mx-auto mb-3" />
                  <p className="text-slate-400">
                    {isDragActive
                      ? 'Drop images here...'
                      : 'Drag & drop images or click to upload'}
                  </p>
                  <p className="text-slate-600 text-sm mt-1">
                    {5 - additionalImages.length} slots remaining
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Pricing Configuration */}
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <DollarSign className="w-5 h-5" />
                License Pricing
              </CardTitle>
              <CardDescription>
                Set your pricing for different license tiers (USD)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {formErrors.pricing && (
                <p className="text-red-500 text-sm">{formErrors.pricing}</p>
              )}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Personal License */}
                <div className="p-4 rounded-lg bg-slate-900/50">
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Personal License
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
                      $
                    </span>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      value={formData.pricing.personal || ''}
                      onChange={(e) => handlePricingChange('personal', e.target.value)}
                      placeholder="0.00"
                      className="bg-slate-800 border-slate-700 pl-7"
                    />
                  </div>
                  <p className="text-slate-500 text-xs mt-2">Non-commercial use</p>
                </div>

                {/* Commercial License */}
                <div className="p-4 rounded-lg bg-slate-900/50">
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Commercial License
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
                      $
                    </span>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      value={formData.pricing.commercial || ''}
                      onChange={(e) => handlePricingChange('commercial', e.target.value)}
                      placeholder="0.00"
                      className="bg-slate-800 border-slate-700 pl-7"
                    />
                  </div>
                  <p className="text-slate-500 text-xs mt-2">Business use</p>
                </div>

                {/* Enterprise License */}
                <div className="p-4 rounded-lg bg-slate-900/50">
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Enterprise License
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
                      $
                    </span>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      value={formData.pricing.enterprise || ''}
                      onChange={(e) => handlePricingChange('enterprise', e.target.value)}
                      placeholder="0.00"
                      className="bg-slate-800 border-slate-700 pl-7"
                    />
                  </div>
                  <p className="text-slate-500 text-xs mt-2">Unlimited use</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Submit Button (Mobile) */}
          <div className="md:hidden">
            <Button
              type="submit"
              disabled={updateMutation.isPending}
              variant="gradient"
              className="w-full"
              size="lg"
            >
              {updateMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save Changes
                </>
              )}
            </Button>
          </div>
        </form>
      </main>
    </div>
  )
}

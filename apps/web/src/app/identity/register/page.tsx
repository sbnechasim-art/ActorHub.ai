'use client'

import { useState, useCallback, useEffect, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import { Camera, Upload, Check, Shield, ArrowLeft, ArrowRight, Loader2, Video } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { identityApi } from '@/lib/api'
import { cn } from '@/lib/utils'
import { logger } from '@/lib/logger'
import { showErrorToast } from '@/lib/errors'
import { validators, validateField } from '@/lib/validation'
import { LiveSelfieCapture, LivenessMetadata } from '@/components/verification'
import { CameraError } from '@/hooks/useCamera'

type Step = 'upload' | 'verify' | 'settings' | 'complete'

const STEPS = ['upload', 'verify', 'settings', 'complete'] as const

interface SelfieData {
  blob: Blob
  base64: string
  livenessMetadata: LivenessMetadata
}

export default function RegisterIdentityPage() {
  const router = useRouter()
  const [step, setStep] = useState<Step>('upload')
  const [faceImage, setFaceImage] = useState<File | null>(null)
  const [facePreview, setFacePreview] = useState<string | null>(null)

  // Selfie data from camera capture
  const [selfieData, setSelfieData] = useState<SelfieData | null>(null)
  const [selfiePreview, setSelfiePreview] = useState<string | null>(null)

  // Manage object URLs properly to avoid memory leaks and DOM errors
  useEffect(() => {
    if (faceImage) {
      const url = URL.createObjectURL(faceImage)
      setFacePreview(url)
      return () => URL.revokeObjectURL(url)
    } else {
      setFacePreview(null)
    }
  }, [faceImage])

  useEffect(() => {
    if (selfieData) {
      const url = URL.createObjectURL(selfieData.blob)
      setSelfiePreview(url)
      return () => URL.revokeObjectURL(url)
    } else {
      setSelfiePreview(null)
    }
  }, [selfieData])

  const [settings, setSettings] = useState({
    displayName: '',
    protectionLevel: 'FREE',
    allowCommercial: false,
    allowAiTraining: false,
    showInPublicGallery: false,
    blockedCategories: [] as string[]
  })

  // Validation errors
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})

  // Validate display name
  const validateDisplayName = (name: string): string | null => {
    return validateField(name, [
      validators.required('Display name'),
      validators.minLength(2, 'Display name'),
      validators.maxLength(50, 'Display name'),
    ])
  }

  // Validate before submit
  const validateForm = (): boolean => {
    const errors: Record<string, string> = {}

    const nameError = validateDisplayName(settings.displayName)
    if (nameError) errors.displayName = nameError

    if (!faceImage) errors.faceImage = 'Face photo is required'
    if (!selfieData) errors.selfie = 'Verification selfie is required'

    setValidationErrors(errors)
    return Object.keys(errors).length === 0
  }

  const registerMutation = useMutation({
    mutationFn: async () => {
      // Validate before submitting
      if (!validateForm()) {
        throw new Error('Please fix the validation errors before submitting')
      }

      const formData = new FormData()
      formData.append('face_image', faceImage!)

      // Convert selfie blob to File for FormData
      const selfieFile = new File([selfieData!.blob], 'selfie.jpg', { type: 'image/jpeg' })
      formData.append('verification_image', selfieFile)

      formData.append('display_name', settings.displayName.trim())
      formData.append('protection_level', settings.protectionLevel)
      formData.append('allow_commercial', String(settings.allowCommercial))
      formData.append('allow_ai_training', String(settings.allowAiTraining))
      formData.append('show_in_public_gallery', String(settings.showInPublicGallery))

      // Add liveness metadata
      formData.append('is_live_capture', 'true')
      formData.append('liveness_metadata', JSON.stringify(selfieData!.livenessMetadata))

      return identityApi.register(formData)
    },
    onSuccess: () => {
      setStep('complete')
      setTimeout(() => router.push('/dashboard'), 3000)
    },
    onError: (error: unknown) => {
      logger.error('Registration error', error)
      showErrorToast(error)
    }
  })

  // Allowed image types and max file size (10MB)
  const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
  const MAX_FILE_SIZE = 10 * 1024 * 1024

  const onDropFace = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // Handle rejected files
    if (rejectedFiles.length > 0) {
      const rejection = rejectedFiles[0]
      if (rejection.errors?.some((e: any) => e.code === 'file-too-large')) {
        setValidationErrors(prev => ({ ...prev, faceImage: 'Image must be less than 10MB' }))
      } else if (rejection.errors?.some((e: any) => e.code === 'file-invalid-type')) {
        setValidationErrors(prev => ({ ...prev, faceImage: 'Only JPG, PNG, and WebP images are allowed' }))
      }
      return
    }

    // Validate accepted file
    const file = acceptedFiles[0]
    if (file) {
      // Clear previous errors
      setValidationErrors(prev => ({ ...prev, faceImage: '' }))

      // Additional validation
      if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
        setValidationErrors(prev => ({ ...prev, faceImage: 'Invalid image type' }))
        return
      }
      if (file.size > MAX_FILE_SIZE) {
        setValidationErrors(prev => ({ ...prev, faceImage: 'Image must be less than 10MB' }))
        return
      }

      setFaceImage(file)
    }
  }, [])

  const faceDropzone = useDropzone({
    onDrop: onDropFace,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp'] },
    maxFiles: 1,
    maxSize: MAX_FILE_SIZE,
    validator: (file) => {
      if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
        return { code: 'file-invalid-type', message: 'Invalid file type' }
      }
      return null
    }
  })

  // Handle selfie capture from camera
  const handleSelfieCapture = useCallback((blob: Blob, base64: string, livenessMetadata: LivenessMetadata) => {
    setSelfieData({ blob, base64, livenessMetadata })
    setStep('settings')
  }, [])

  const handleSelfieCaptureError = useCallback((error: CameraError) => {
    logger.error('Camera error', { error })
    // Error is displayed in the LiveSelfieCapture component
  }, [])

  const handleSelfieCaptureCancel = useCallback(() => {
    setStep('upload')
  }, [])

  const currentStepIndex = STEPS.indexOf(step)

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800">
        <div className="container mx-auto px-4 h-16 flex items-center">
          <Link href="/dashboard" className="flex items-center gap-2 text-slate-400 hover:text-white transition">
            <ArrowLeft className="w-5 h-5" />
            Back to Dashboard
          </Link>
        </div>
      </header>

      <main className="container mx-auto px-4 py-12 max-w-2xl">
        {/* Progress Steps */}
        <div className="flex items-center justify-center mb-12">
          {STEPS.map((s, i) => (
            <div key={s} className="flex items-center">
              <div
                className={cn(
                  'w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-colors',
                  i < currentStepIndex
                    ? 'bg-green-500 text-white'
                    : i === currentStepIndex
                    ? 'bg-blue-500 text-white'
                    : 'bg-slate-800 text-slate-500'
                )}
              >
                {i < currentStepIndex ? <Check className="w-5 h-5" /> : i + 1}
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={cn(
                    'w-16 h-0.5 mx-2',
                    i < currentStepIndex ? 'bg-green-500' : 'bg-slate-800'
                  )}
                />
              )}
            </div>
          ))}
        </div>

        <AnimatePresence mode="wait">
          {/* Step 1: Upload Face Photo */}
          {step === 'upload' && (
            <motion.div
              key="upload"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
              className="text-center"
            >
              <div className="w-16 h-16 rounded-full bg-blue-500/20 flex items-center justify-center mx-auto mb-6">
                <Camera className="w-8 h-8 text-blue-400" />
              </div>
              <h1 className="text-2xl font-bold text-white mb-2">Upload Your Photo</h1>
              <p className="text-slate-400 mb-8">
                A clear, front-facing photo with good lighting works best
              </p>

              <div
                {...faceDropzone.getRootProps()}
                className={cn(
                  'border-2 border-dashed rounded-xl p-12 cursor-pointer transition-colors',
                  faceDropzone.isDragActive
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-slate-700 hover:border-slate-600'
                )}
              >
                <input {...faceDropzone.getInputProps()} />
                {faceImage && facePreview ? (
                  <div className="flex flex-col items-center">
                    <img
                      src={facePreview}
                      alt="Preview"
                      className="w-48 h-48 object-cover rounded-xl mb-4"
                    />
                    <p className="text-green-400 flex items-center gap-2">
                      <Check className="w-4 h-4" />
                      Photo uploaded
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center">
                    <Upload className="w-12 h-12 text-slate-500 mb-4" />
                    <p className="text-slate-400">Drag & drop or click to upload</p>
                    <p className="text-slate-600 text-sm mt-2">JPG, PNG up to 10MB</p>
                  </div>
                )}
              </div>

              <Button
                onClick={() => setStep('verify')}
                disabled={!faceImage}
                variant="gradient"
                size="lg"
                className="mt-8"
              >
                Continue
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </motion.div>
          )}

          {/* Step 2: Live Selfie Verification */}
          {step === 'verify' && (
            <motion.div
              key="verify"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
            >
              <div className="text-center mb-8">
                <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-6">
                  <Video className="w-8 h-8 text-green-400" />
                </div>
                <h1 className="text-2xl font-bold text-white mb-2">Take a Live Selfie</h1>
                <p className="text-slate-400">
                  We need to verify you're the person in the photo
                </p>
              </div>

              {/* Side-by-side comparison if selfie already taken */}
              {selfieData && selfiePreview ? (
                <div className="mb-8">
                  <div className="grid grid-cols-2 gap-6 mb-6">
                    <div className="text-center">
                      <p className="text-slate-400 text-sm mb-2">Your Photo</p>
                      <img
                        src={facePreview!}
                        alt="Reference"
                        className="w-full aspect-square object-cover rounded-xl"
                      />
                    </div>
                    <div className="text-center">
                      <p className="text-slate-400 text-sm mb-2">Live Selfie</p>
                      <img
                        src={selfiePreview}
                        alt="Selfie"
                        className="w-full aspect-square object-cover rounded-xl"
                      />
                    </div>
                  </div>
                  <div className="flex gap-4 justify-center">
                    <Button variant="outline" onClick={() => setSelfieData(null)}>
                      Retake Selfie
                    </Button>
                    <Button variant="gradient" onClick={() => setStep('settings')}>
                      Continue
                      <ArrowRight className="w-5 h-5 ml-2" />
                    </Button>
                  </div>
                </div>
              ) : (
                <LiveSelfieCapture
                  onCapture={handleSelfieCapture}
                  onError={handleSelfieCaptureError}
                  onCancel={handleSelfieCaptureCancel}
                  enableLivenessCheck={true}
                />
              )}

              {/* Back button when in camera mode */}
              {!selfieData && (
                <Button
                  variant="ghost"
                  onClick={() => setStep('upload')}
                  className="mt-4 w-full text-slate-400"
                >
                  <ArrowLeft className="w-5 h-5 mr-2" />
                  Back to Photo Upload
                </Button>
              )}
            </motion.div>
          )}

          {/* Step 3: Settings */}
          {step === 'settings' && (
            <motion.div
              key="settings"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
            >
              <h1 className="text-2xl font-bold text-white mb-8 text-center">
                Protection Settings
              </h1>

              {/* Photo comparison summary */}
              <div className="grid grid-cols-2 gap-4 mb-8">
                <div className="bg-slate-800/50 rounded-xl p-4 text-center">
                  <img
                    src={facePreview!}
                    alt="Reference"
                    className="w-24 h-24 object-cover rounded-lg mx-auto mb-2"
                  />
                  <p className="text-slate-400 text-sm">Reference Photo</p>
                </div>
                <div className="bg-slate-800/50 rounded-xl p-4 text-center">
                  <img
                    src={selfiePreview!}
                    alt="Selfie"
                    className="w-24 h-24 object-cover rounded-lg mx-auto mb-2"
                  />
                  <p className="text-slate-400 text-sm flex items-center justify-center gap-1">
                    <Check className="w-4 h-4 text-green-400" />
                    Live Selfie
                  </p>
                </div>
              </div>

              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-6 space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Display Name
                    </label>
                    <Input
                      value={settings.displayName}
                      onChange={(e) => {
                        setSettings({ ...settings, displayName: e.target.value })
                        // Clear error on change
                        if (validationErrors.displayName) {
                          setValidationErrors(prev => ({ ...prev, displayName: '' }))
                        }
                      }}
                      placeholder="How you want to be identified"
                      className={cn(
                        "bg-slate-900 border-slate-700",
                        validationErrors.displayName && "border-red-500 focus:border-red-500"
                      )}
                    />
                    {validationErrors.displayName && (
                      <p className="text-red-400 text-sm mt-1">{validationErrors.displayName}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Protection Level
                    </label>
                    <div className="grid grid-cols-3 gap-3">
                      {['FREE', 'PRO', 'ENTERPRISE'].map((level) => (
                        <button
                          key={level}
                          onClick={() => setSettings({ ...settings, protectionLevel: level })}
                          className={cn(
                            'p-4 rounded-lg border text-center capitalize transition-colors',
                            settings.protectionLevel === level
                              ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                              : 'border-slate-700 text-slate-400 hover:border-slate-600'
                          )}
                        >
                          {level.toLowerCase()}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-3">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.allowCommercial}
                        onChange={(e) => setSettings({ ...settings, allowCommercial: e.target.checked })}
                        className="w-5 h-5 rounded border-slate-700 bg-slate-900"
                      />
                      <span className="text-slate-300">
                        Allow commercial use (earn money when brands use your likeness)
                      </span>
                    </label>

                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.allowAiTraining}
                        onChange={(e) => setSettings({ ...settings, allowAiTraining: e.target.checked })}
                        className="w-5 h-5 rounded border-slate-700 bg-slate-900"
                      />
                      <span className="text-slate-300">
                        Allow AI training (your data may be used to improve AI models)
                      </span>
                    </label>

                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.showInPublicGallery}
                        onChange={(e) => setSettings({ ...settings, showInPublicGallery: e.target.checked })}
                        className="w-5 h-5 rounded border-slate-700 bg-slate-900"
                      />
                      <span className="text-slate-300">
                        Show my verified image in public gallery
                      </span>
                    </label>
                  </div>
                </CardContent>
              </Card>

              <div className="flex gap-4 justify-center mt-8">
                <Button variant="outline" onClick={() => setStep('verify')}>
                  <ArrowLeft className="w-5 h-5 mr-2" />
                  Back
                </Button>
                <Button
                  onClick={() => registerMutation.mutate()}
                  disabled={!settings.displayName || registerMutation.isPending}
                  variant="gradient"
                  size="lg"
                >
                  {registerMutation.isPending ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      Registering...
                    </>
                  ) : (
                    <>
                      Complete Registration
                      <Check className="w-5 h-5 ml-2" />
                    </>
                  )}
                </Button>
              </div>
            </motion.div>
          )}

          {/* Step 4: Complete */}
          {step === 'complete' && (
            <motion.div
              key="complete"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.2 }}
              className="text-center"
            >
              <div className="w-20 h-20 rounded-full bg-green-500 flex items-center justify-center mx-auto mb-6">
                <Check className="w-10 h-10 text-white" />
              </div>
              <h1 className="text-3xl font-bold text-white mb-2">You're Protected!</h1>
              <p className="text-slate-400 mb-8">
                Your digital identity is now registered and protected.
                Redirecting to dashboard...
              </p>
              <div className="flex justify-center">
                <Loader2 className="w-6 h-6 text-slate-500 animate-spin" />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}

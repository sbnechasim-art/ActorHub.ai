'use client'

import { useState, useCallback, useEffect, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import { Camera, Upload, Check, Shield, ArrowLeft, ArrowRight, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { identityApi } from '@/lib/api'
import { cn } from '@/lib/utils'

type Step = 'upload' | 'verify' | 'settings' | 'complete'

const STEPS = ['upload', 'verify', 'settings', 'complete'] as const

export default function RegisterIdentityPage() {
  const router = useRouter()
  const [step, setStep] = useState<Step>('upload')
  const [faceImage, setFaceImage] = useState<File | null>(null)
  const [verifyImage, setVerifyImage] = useState<File | null>(null)
  const [facePreview, setFacePreview] = useState<string | null>(null)
  const [verifyPreview, setVerifyPreview] = useState<string | null>(null)

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
    if (verifyImage) {
      const url = URL.createObjectURL(verifyImage)
      setVerifyPreview(url)
      return () => URL.revokeObjectURL(url)
    } else {
      setVerifyPreview(null)
    }
  }, [verifyImage])
  const [settings, setSettings] = useState({
    displayName: '',
    protectionLevel: 'free',
    allowCommercial: false,
    allowAiTraining: false,
    blockedCategories: [] as string[]
  })

  const registerMutation = useMutation({
    mutationFn: async () => {
      const formData = new FormData()
      formData.append('face_image', faceImage!)
      formData.append('verification_image', verifyImage!)
      formData.append('display_name', settings.displayName)
      formData.append('protection_level', settings.protectionLevel)
      formData.append('allow_commercial', String(settings.allowCommercial))
      formData.append('allow_ai_training', String(settings.allowAiTraining))

      return identityApi.register(formData)
    },
    onSuccess: () => {
      setStep('complete')
      setTimeout(() => router.push('/dashboard'), 3000)
    },
    onError: (error: any) => {
      // Handle FastAPI validation errors (detail can be array of objects)
      let errorMessage = 'Registration failed'
      const detail = error.response?.data?.detail
      const status = error.response?.status

      if (status === 401) {
        errorMessage = 'You must be logged in to register an identity. Please sign in first.'
      } else if (typeof detail === 'string') {
        errorMessage = detail
      } else if (Array.isArray(detail) && detail.length > 0) {
        errorMessage = detail.map((d: any) => d.msg || d.message || JSON.stringify(d)).join(', ')
      } else if (error.message) {
        errorMessage = error.message
      }

      console.error('Registration error:', { status, detail, error })
      alert(errorMessage)
    }
  })

  const onDropFace = useCallback((files: File[]) => {
    if (files[0]) setFaceImage(files[0])
  }, [])

  const onDropVerify = useCallback((files: File[]) => {
    if (files[0]) setVerifyImage(files[0])
  }, [])

  const faceDropzone = useDropzone({
    onDrop: onDropFace,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png'] },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024
  })

  const verifyDropzone = useDropzone({
    onDrop: onDropVerify,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png'] },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024
  })

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

          {/* Step 2: Verification Selfie */}
          {step === 'verify' && (
            <motion.div
              key="verify"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
              className="text-center"
            >
              <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-6">
                <Shield className="w-8 h-8 text-green-400" />
              </div>
              <h1 className="text-2xl font-bold text-white mb-2">Verify It's You</h1>
              <p className="text-slate-400 mb-8">
                Take a selfie or upload a verification photo
              </p>

              <div
                {...verifyDropzone.getRootProps()}
                className={cn(
                  'border-2 border-dashed rounded-xl p-12 cursor-pointer transition-colors',
                  verifyDropzone.isDragActive
                    ? 'border-green-500 bg-green-500/10'
                    : 'border-slate-700 hover:border-slate-600'
                )}
              >
                <input {...verifyDropzone.getInputProps()} />
                {verifyImage && verifyPreview ? (
                  <div className="flex flex-col items-center">
                    <img
                      src={verifyPreview}
                      alt="Verification"
                      className="w-48 h-48 object-cover rounded-xl mb-4"
                    />
                    <p className="text-green-400 flex items-center gap-2">
                      <Check className="w-4 h-4" />
                      Verification photo uploaded
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center">
                    <Camera className="w-12 h-12 text-slate-500 mb-4" />
                    <p className="text-slate-400">Upload verification photo</p>
                  </div>
                )}
              </div>

              <div className="flex gap-4 justify-center mt-8">
                <Button variant="outline" onClick={() => setStep('upload')}>
                  <ArrowLeft className="w-5 h-5 mr-2" />
                  Back
                </Button>
                <Button
                  onClick={() => setStep('settings')}
                  disabled={!verifyImage}
                  variant="gradient"
                >
                  Continue
                  <ArrowRight className="w-5 h-5 ml-2" />
                </Button>
              </div>
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

              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-6 space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Display Name
                    </label>
                    <Input
                      value={settings.displayName}
                      onChange={(e) => setSettings({ ...settings, displayName: e.target.value })}
                      placeholder="How you want to be identified"
                      className="bg-slate-900 border-slate-700"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Protection Level
                    </label>
                    <div className="grid grid-cols-3 gap-3">
                      {['free', 'pro', 'enterprise'].map((level) => (
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
                          {level}
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

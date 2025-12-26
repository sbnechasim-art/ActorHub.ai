'use client'

import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { RotateCcw, Check } from 'lucide-react'

interface CaptureConfirmationProps {
  imageBlob: Blob
  onConfirm: () => void
  onRetake: () => void
  className?: string
}

export function CaptureConfirmation({
  imageBlob,
  onConfirm,
  onRetake,
  className,
}: CaptureConfirmationProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(null)

  useEffect(() => {
    const url = URL.createObjectURL(imageBlob)
    setImageUrl(url)

    return () => {
      URL.revokeObjectURL(url)
    }
  }, [imageBlob])

  return (
    <div className={cn('flex flex-col', className)}>
      {/* Captured image preview */}
      <div className="relative aspect-[4/3] rounded-lg overflow-hidden bg-black mb-4">
        {imageUrl && (
          <img
            src={imageUrl}
            alt="Captured selfie"
            className="w-full h-full object-cover"
          />
        )}

        {/* Success indicator */}
        <div className="absolute top-4 right-4 bg-green-500 rounded-full p-2">
          <Check className="w-5 h-5 text-white" />
        </div>
      </div>

      {/* Confirmation text */}
      <p className="text-center text-gray-300 mb-6">
        Does this photo look good? Make sure your face is clearly visible.
      </p>

      {/* Action buttons */}
      <div className="flex gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={onRetake}
          className="flex-1"
        >
          <RotateCcw className="w-4 h-4 mr-2" />
          Retake
        </Button>
        <Button
          type="button"
          variant="gradient"
          onClick={onConfirm}
          className="flex-1"
        >
          <Check className="w-4 h-4 mr-2" />
          Use This Photo
        </Button>
      </div>
    </div>
  )
}

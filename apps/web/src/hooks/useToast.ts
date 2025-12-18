'use client'

import { useState, useCallback } from 'react'

export interface Toast {
  id: string
  title: string
  description?: string
  variant: 'default' | 'destructive' | 'success'
  duration?: number
}

interface ToastState {
  toasts: Toast[]
}

let toastIdCounter = 0

const listeners: Set<(state: ToastState) => void> = new Set()
let toastState: ToastState = { toasts: [] }

function notifyListeners() {
  listeners.forEach((listener) => listener(toastState))
}

function addToast(toast: Omit<Toast, 'id'>) {
  const id = `toast-${++toastIdCounter}`
  const newToast: Toast = { ...toast, id }

  toastState = {
    toasts: [...toastState.toasts, newToast],
  }
  notifyListeners()

  // Auto dismiss after duration
  const duration = toast.duration ?? 5000
  if (duration > 0) {
    setTimeout(() => {
      dismissToast(id)
    }, duration)
  }

  return id
}

function dismissToast(id: string) {
  toastState = {
    toasts: toastState.toasts.filter((t) => t.id !== id),
  }
  notifyListeners()
}

export function useToast() {
  const [state, setState] = useState<ToastState>(toastState)

  useState(() => {
    listeners.add(setState)
    return () => {
      listeners.delete(setState)
    }
  })

  const toast = useCallback((props: Omit<Toast, 'id'>) => {
    return addToast(props)
  }, [])

  const dismiss = useCallback((id: string) => {
    dismissToast(id)
  }, [])

  return {
    toasts: state.toasts,
    toast,
    dismiss,
  }
}

// Convenience functions for common toast types
export const toast = {
  success: (title: string, description?: string) =>
    addToast({ title, description, variant: 'success' }),
  error: (title: string, description?: string) =>
    addToast({ title, description, variant: 'destructive' }),
  info: (title: string, description?: string) =>
    addToast({ title, description, variant: 'default' }),
}

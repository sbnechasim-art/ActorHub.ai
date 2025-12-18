import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

type Tab = 'capture' | 'train' | 'export' | 'settings'

interface TrainingImage {
  id: string
  path: string
  preview: string
}

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('capture')
  const [images, setImages] = useState<TrainingImage[]>([])
  const [isTraining, setIsTraining] = useState(false)
  const [trainingProgress, setTrainingProgress] = useState(0)
  const [version, setVersion] = useState('')

  useEffect(() => {
    // Get app version
    window.api?.getVersion().then(setVersion)

    // Listen for training progress
    const unsubProgress = window.api?.onTrainingProgress((progress, step) => {
      setTrainingProgress(progress)
    })

    const unsubComplete = window.api?.onTrainingComplete((result) => {
      setIsTraining(false)
      setTrainingProgress(100)
    })

    return () => {
      unsubProgress?.()
      unsubComplete?.()
    }
  }, [])

  const handleAddImages = async () => {
    const paths = await window.api?.openMultiple({
      filters: [{ name: 'Images', extensions: ['jpg', 'jpeg', 'png', 'webp'] }]
    })

    if (paths && paths.length > 0) {
      const newImages = paths.map((path: string) => ({
        id: Math.random().toString(36).substr(2, 9),
        path,
        preview: `file://${path}`
      }))
      setImages([...images, ...newImages])
    }
  }

  const tabs = [
    { id: 'capture', label: 'Capture', icon: '📷' },
    { id: 'train', label: 'Train', icon: '🧠' },
    { id: 'export', label: 'Export', icon: '📦' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
  ]

  return (
    <div className="flex h-screen bg-slate-950">
      {/* Sidebar */}
      <div className="w-64 border-r border-slate-800 flex flex-col">
        {/* App Header */}
        <div className="p-4 border-b border-slate-800" style={{ WebkitAppRegion: 'drag' } as any}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-xl">
              🎭
            </div>
            <div>
              <h1 className="font-bold text-white">ActorHub Studio</h1>
              <p className="text-xs text-slate-500">v{version || '1.0.0'}</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2" style={{ WebkitAppRegion: 'no-drag' } as any}>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as Tab)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-purple-600 text-white'
                  : 'text-slate-400 hover:bg-slate-800'
              }`}
            >
              <span className="text-lg">{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>

        {/* Training Status */}
        {isTraining && (
          <div className="p-4 border-t border-slate-800">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-sm text-slate-300">Training in progress...</span>
            </div>
            <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-blue-500 to-purple-600"
                initial={{ width: 0 }}
                animate={{ width: `${trainingProgress}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>
            <p className="text-xs text-slate-500 mt-1">{trainingProgress}% complete</p>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Tab Content */}
        <div className="flex-1 p-6 overflow-auto">
          {activeTab === 'capture' && (
            <div>
              <h2 className="text-2xl font-bold text-white mb-6">Capture Training Data</h2>

              {/* Upload Area */}
              <div
                onClick={handleAddImages}
                className="border-2 border-dashed border-slate-700 rounded-xl p-12 text-center cursor-pointer hover:border-purple-500 transition-colors mb-6"
              >
                <div className="text-5xl mb-4">📸</div>
                <p className="text-slate-400">
                  Click to add photos or drag and drop
                </p>
                <p className="text-sm text-slate-600 mt-2">
                  JPG, PNG, WebP - at least 10 photos recommended
                </p>
              </div>

              {/* Image Grid */}
              {images.length > 0 && (
                <div className="grid grid-cols-4 gap-4">
                  {images.map((img) => (
                    <div
                      key={img.id}
                      className="aspect-square rounded-lg overflow-hidden bg-slate-800 relative group"
                    >
                      <img
                        src={img.preview}
                        alt=""
                        className="w-full h-full object-cover"
                      />
                      <button
                        onClick={() => setImages(images.filter((i) => i.id !== img.id))}
                        className="absolute top-2 right-2 w-6 h-6 rounded-full bg-red-500 text-white text-xs opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Stats */}
              {images.length > 0 && (
                <div className="mt-6 p-4 bg-slate-800/50 rounded-lg">
                  <p className="text-slate-400">
                    {images.length} images added
                    {images.length < 10 && (
                      <span className="text-yellow-500 ml-2">
                        (Add {10 - images.length} more for best results)
                      </span>
                    )}
                  </p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'train' && (
            <div>
              <h2 className="text-2xl font-bold text-white mb-6">Train Actor Pack</h2>

              {images.length < 5 ? (
                <div className="text-center py-20">
                  <div className="text-5xl mb-4">🖼️</div>
                  <p className="text-slate-400 mb-4">
                    Add at least 5 images to start training
                  </p>
                  <button
                    onClick={() => setActiveTab('capture')}
                    className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                  >
                    Add Images
                  </button>
                </div>
              ) : (
                <div className="max-w-xl mx-auto text-center py-12">
                  <div className="text-6xl mb-6">🧠</div>
                  <h3 className="text-xl font-semibold text-white mb-4">
                    Ready to Train
                  </h3>
                  <p className="text-slate-400 mb-8">
                    {images.length} images selected for training.
                    This will create your personalized Actor Pack.
                  </p>
                  <button
                    onClick={() => setIsTraining(true)}
                    disabled={isTraining}
                    className="px-8 py-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-xl font-semibold hover:from-blue-600 hover:to-purple-700 transition-colors disabled:opacity-50"
                  >
                    {isTraining ? 'Training...' : 'Start Training'}
                  </button>
                </div>
              )}
            </div>
          )}

          {activeTab === 'export' && (
            <div>
              <h2 className="text-2xl font-bold text-white mb-6">Export Actor Pack</h2>
              <div className="text-center py-20">
                <div className="text-5xl mb-4">📦</div>
                <p className="text-slate-400">
                  Complete training first to export your Actor Pack
                </p>
              </div>
            </div>
          )}

          {activeTab === 'settings' && (
            <div>
              <h2 className="text-2xl font-bold text-white mb-6">Settings</h2>
              <div className="space-y-6 max-w-xl">
                <div className="p-4 bg-slate-800/50 rounded-lg">
                  <h3 className="font-semibold text-white mb-2">API Configuration</h3>
                  <input
                    type="password"
                    placeholder="Enter your ActorHub API key"
                    className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white"
                  />
                </div>
                <div className="p-4 bg-slate-800/50 rounded-lg">
                  <h3 className="font-semibold text-white mb-2">Training Quality</h3>
                  <select className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white">
                    <option>Standard (faster)</option>
                    <option>High Quality (recommended)</option>
                    <option>Maximum (slower)</option>
                  </select>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Type declarations for window.api
declare global {
  interface Window {
    api?: {
      openFile: (options?: { filters?: { name: string; extensions: string[] }[] }) => Promise<string[]>
      openMultiple: (options?: { filters?: { name: string; extensions: string[] }[] }) => Promise<string[]>
      saveFile: (options?: { defaultPath?: string; filters?: { name: string; extensions: string[] }[] }) => Promise<string | undefined>
      getVersion: () => Promise<string>
      onTrainingProgress: (callback: (progress: number, step: string) => void) => () => void
      onTrainingComplete: (callback: (result: any) => void) => () => void
      onTrainingError: (callback: (error: string) => void) => () => void
    }
  }
}

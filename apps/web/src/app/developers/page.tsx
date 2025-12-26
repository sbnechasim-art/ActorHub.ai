'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Code,
  Key,
  Shield,
  Zap,
  Book,
  Terminal,
  ArrowRight,
  Check,
  Copy
} from 'lucide-react'
import { useState } from 'react'
import { logger } from '@/lib/logger'

// API documentation URL - configurable via environment variable
const API_DOCS_URL = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL.replace('/api/v1', '')}/docs`
  : 'http://localhost:8000/docs'

export default function DevelopersPage() {
  const [copied, setCopied] = useState<string | null>(null)

  const copyToClipboard = async (text: string, id: string) => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text)
      } else {
        // Fallback for older browsers or non-secure contexts
        const textArea = document.createElement('textarea')
        textArea.value = text
        textArea.style.position = 'fixed'
        textArea.style.left = '-999999px'
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
      }
      setCopied(id)
      setTimeout(() => setCopied(null), 2000)
    } catch (err) {
      logger.error('Failed to copy text', err as Error)
    }
  }

  const codeExamples = {
    verify: `import requests

response = requests.post(
    "https://api.actorhub.ai/v1/identity/verify",
    headers={"X-API-Key": "your_api_key"},
    files={"image": open("face.jpg", "rb")}
)

result = response.json()
print(f"Match found: {result['matched']}")
print(f"Identity: {result['identity']['name']}")`,

    python: `pip install actorhub

from actorhub import ActorHub

client = ActorHub(api_key="your_api_key")

# Verify a face
result = client.identity.verify(
    image="path/to/image.jpg"
)

if result.matched:
    print(f"Protected identity: {result.identity.name}")
    print(f"Allowed: {result.allowed}")`,

    javascript: `npm install @actorhub/sdk

import { ActorHub } from '@actorhub/sdk';

const client = new ActorHub({ apiKey: 'your_api_key' });

// Verify a face
const result = await client.identity.verify({
  image: imageFile
});

if (result.matched) {
  console.log(\`Protected identity: \${result.identity.name}\`);
  console.log(\`Allowed: \${result.allowed}\`);
}`
  }

  const features = [
    {
      icon: Shield,
      title: 'Face Verification API',
      description: 'Check if a face belongs to a protected identity in milliseconds',
    },
    {
      icon: Zap,
      title: 'Real-time Processing',
      description: 'Sub-100ms response times with 99.9% uptime SLA',
    },
    {
      icon: Key,
      title: 'Secure API Keys',
      description: 'Granular permissions and rate limiting per key',
    },
    {
      icon: Code,
      title: 'SDKs & Libraries',
      description: 'Official SDKs for Python, JavaScript, Go, and more',
    },
  ]

  const endpoints = [
    { method: 'POST', path: '/v1/identity/verify', description: 'Verify a face against protected identities' },
    { method: 'GET', path: '/v1/identity/{id}', description: 'Get identity details and permissions' },
    { method: 'POST', path: '/v1/license/check', description: 'Check if usage is licensed' },
    { method: 'GET', path: '/v1/marketplace/listings', description: 'Browse available Actor Packs' },
    { method: 'POST', path: '/v1/actor-packs/train', description: 'Train a new Actor Pack' },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-900 to-black">
      {/* Header */}
      <header className="border-b border-gray-800">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center space-x-2">
            <Shield className="w-8 h-8 text-purple-500" />
            <span className="text-xl font-bold text-white">ActorHub.ai</span>
          </Link>
          <nav className="flex items-center space-x-6">
            <Link href="/marketplace" className="text-gray-300 hover:text-white">
              Marketplace
            </Link>
            <Link href="/developers" className="text-purple-400">
              Developers
            </Link>
            <Link href={API_DOCS_URL} target="_blank" rel="noopener noreferrer">
              <Button variant="outline" className="border-gray-700 text-gray-300">
                API Docs
              </Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="py-20">
        <div className="container mx-auto px-4 text-center">
          <div className="inline-flex items-center px-4 py-2 bg-purple-500/10 rounded-full text-purple-400 text-sm mb-6">
            <Terminal className="w-4 h-4 mr-2" />
            Developer Platform
          </div>
          <h1 className="text-5xl font-bold text-white mb-6">
            Build with ActorHub.ai API
          </h1>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-8">
            Integrate identity verification and AI licensing into your platform with our powerful API
          </p>
          <div className="flex justify-center space-x-4">
            <Link href={API_DOCS_URL} target="_blank" rel="noopener noreferrer">
              <Button size="lg" className="bg-purple-600 hover:bg-purple-700">
                <Book className="w-5 h-5 mr-2" />
                View API Docs
              </Button>
            </Link>
            <Link href="/dashboard">
              <Button size="lg" variant="outline" className="border-gray-700 text-gray-300">
                Get API Key
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 border-t border-gray-800">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <Card key={index} className="bg-gray-800/30 border-gray-700">
                <CardHeader>
                  <feature.icon className="w-10 h-10 text-purple-400 mb-2" />
                  <CardTitle className="text-white">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-400">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Quick Start */}
      <section className="py-16 border-t border-gray-800">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-white text-center mb-12">Quick Start</h2>

          <div className="max-w-4xl mx-auto">
            <div className="grid md:grid-cols-2 gap-6 mb-8">
              {/* Python Example */}
              <Card className="bg-gray-800/30 border-gray-700">
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-white text-lg">Python</CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(codeExamples.python, 'python')}
                    className="text-gray-400 hover:text-white"
                    aria-label={copied === 'python' ? 'Copied Python code' : 'Copy Python code'}
                  >
                    {copied === 'python' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </Button>
                </CardHeader>
                <CardContent>
                  <pre className="bg-gray-900 p-4 rounded-lg text-sm text-gray-300 overflow-x-auto">
                    <code>{codeExamples.python}</code>
                  </pre>
                </CardContent>
              </Card>

              {/* JavaScript Example */}
              <Card className="bg-gray-800/30 border-gray-700">
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-white text-lg">JavaScript</CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(codeExamples.javascript, 'javascript')}
                    className="text-gray-400 hover:text-white"
                    aria-label={copied === 'javascript' ? 'Copied JavaScript code' : 'Copy JavaScript code'}
                  >
                    {copied === 'javascript' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </Button>
                </CardHeader>
                <CardContent>
                  <pre className="bg-gray-900 p-4 rounded-lg text-sm text-gray-300 overflow-x-auto">
                    <code>{codeExamples.javascript}</code>
                  </pre>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* API Endpoints */}
      <section className="py-16 border-t border-gray-800">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-white text-center mb-12">API Endpoints</h2>

          <div className="max-w-4xl mx-auto">
            <Card className="bg-gray-800/30 border-gray-700">
              <CardContent className="p-0">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="text-left p-4 text-gray-400 font-medium">Method</th>
                      <th className="text-left p-4 text-gray-400 font-medium">Endpoint</th>
                      <th className="text-left p-4 text-gray-400 font-medium">Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {endpoints.map((endpoint, index) => (
                      <tr key={index} className="border-b border-gray-700/50 last:border-0">
                        <td className="p-4">
                          <span className={`px-2 py-1 rounded text-xs font-mono ${
                            endpoint.method === 'GET' ? 'bg-green-500/20 text-green-400' : 'bg-blue-500/20 text-blue-400'
                          }`}>
                            {endpoint.method}
                          </span>
                        </td>
                        <td className="p-4 font-mono text-purple-400">{endpoint.path}</td>
                        <td className="p-4 text-gray-300">{endpoint.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>

            <div className="text-center mt-8">
              <Link href={API_DOCS_URL} target="_blank" rel="noopener noreferrer">
                <Button className="bg-purple-600 hover:bg-purple-700">
                  View Full API Documentation
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-8">
        <div className="container mx-auto px-4 text-center text-gray-500">
          <p>&copy; 2024 ActorHub.ai. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}

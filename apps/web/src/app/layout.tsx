import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { Providers } from '@/providers'
import { Toaster } from '@/components/ui/toaster'
import { CartDrawer } from '@/components/cart'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'ActorHub.ai - Digital Identity Protection & Marketplace',
  description: 'Protect your digital identity and monetize your likeness with AI-powered licensing. The global platform for face and identity rights management.',
  keywords: ['digital identity', 'AI protection', 'face recognition', 'actor marketplace', 'deepfake protection'],
  authors: [{ name: 'ActorHub.ai' }],
  openGraph: {
    title: 'ActorHub.ai - Digital Identity Protection',
    description: 'Protect your digital identity and monetize your likeness',
    url: 'https://actorhub.ai',
    siteName: 'ActorHub.ai',
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <Providers>
          {children}
          <Toaster />
          <CartDrawer />
        </Providers>
      </body>
    </html>
  )
}

import { FileQuestion, Home, Search } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function NotFound() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-4">
      <div className="max-w-lg w-full text-center">
        {/* 404 Illustration */}
        <div className="relative mb-8">
          <div className="text-[150px] font-bold text-slate-800/50 leading-none select-none">
            404
          </div>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-24 h-24 rounded-full bg-purple-500/20 flex items-center justify-center">
              <FileQuestion className="w-12 h-12 text-purple-400" />
            </div>
          </div>
        </div>

        {/* Message */}
        <h1 className="text-3xl font-bold text-white mb-4" suppressHydrationWarning>
          Page Not Found
        </h1>
        <p className="text-slate-400 mb-8 text-lg">
          The page you're looking for doesn't exist or has been moved.
          Let's get you back on track.
        </p>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Button
            asChild
            className="bg-purple-600 hover:bg-purple-700"
          >
            <Link href="/">
              <Home className="w-4 h-4 mr-2" />
              Go Home
            </Link>
          </Button>
          <Button
            asChild
            variant="outline"
            className="border-slate-700 text-slate-300 hover:bg-slate-800"
          >
            <Link href="/marketplace">
              <Search className="w-4 h-4 mr-2" />
              Browse Marketplace
            </Link>
          </Button>
        </div>

        {/* Quick Links */}
        <div className="mt-12 pt-8 border-t border-slate-800">
          <p className="text-slate-500 text-sm mb-4">Popular destinations:</p>
          <div className="flex flex-wrap gap-2 justify-center">
            <Link
              href="/dashboard"
              className="px-3 py-1 rounded-full bg-slate-800 text-slate-400 text-sm hover:bg-slate-700 hover:text-white transition-colors"
            >
              Dashboard
            </Link>
            <Link
              href="/identity/register"
              className="px-3 py-1 rounded-full bg-slate-800 text-slate-400 text-sm hover:bg-slate-700 hover:text-white transition-colors"
            >
              Register Identity
            </Link>
            <Link
              href="/marketplace"
              className="px-3 py-1 rounded-full bg-slate-800 text-slate-400 text-sm hover:bg-slate-700 hover:text-white transition-colors"
            >
              Marketplace
            </Link>
            <Link
              href="/pricing"
              className="px-3 py-1 rounded-full bg-slate-800 text-slate-400 text-sm hover:bg-slate-700 hover:text-white transition-colors"
            >
              Pricing
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

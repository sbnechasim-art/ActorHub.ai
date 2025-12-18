'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  User,
  Shield,
  CreditCard,
  Bell,
  Key,
  Trash2,
  Save,
  Plus,
  Copy,
  Eye,
  EyeOff,
} from 'lucide-react'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile')
  const [showApiKey, setShowApiKey] = useState(false)

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'billing', label: 'Billing', icon: CreditCard },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'api-keys', label: 'API Keys', icon: Key },
  ]

  const apiKeys = [
    { id: 1, name: 'Development Key', prefix: 'ah_test_', created: '2024-01-15', lastUsed: '2024-01-20' },
    { id: 2, name: 'Production Key', prefix: 'ah_live_', created: '2024-01-10', lastUsed: '2024-01-19' },
  ]

  return (
    <div className="min-h-screen bg-gray-900 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-white mb-8">Settings</h1>

        <div className="flex gap-8">
          {/* Sidebar */}
          <div className="w-64 space-y-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition ${
                  activeTab === tab.id
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <tab.icon className="w-5 h-5" />
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="flex-1">
            {activeTab === 'profile' && (
              <Card className="bg-gray-800/50 border-gray-700">
                <CardHeader>
                  <CardTitle className="text-white">Profile Settings</CardTitle>
                  <CardDescription className="text-gray-400">
                    Manage your account information
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center space-x-6">
                    <div className="w-24 h-24 bg-purple-600 rounded-full flex items-center justify-center text-3xl text-white">
                      JD
                    </div>
                    <Button variant="outline" className="border-gray-700 text-gray-300">
                      Change Avatar
                    </Button>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-sm text-gray-300">First Name</label>
                      <Input
                        defaultValue="Test"
                        className="bg-gray-900/50 border-gray-700 text-white"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm text-gray-300">Last Name</label>
                      <Input
                        defaultValue="User"
                        className="bg-gray-900/50 border-gray-700 text-white"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm text-gray-300">Email</label>
                    <Input
                      type="email"
                      defaultValue="test@actorhub.ai"
                      className="bg-gray-900/50 border-gray-700 text-white"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm text-gray-300">Display Name</label>
                    <Input
                      defaultValue="TestUser"
                      className="bg-gray-900/50 border-gray-700 text-white"
                    />
                  </div>

                  <Button className="bg-purple-600 hover:bg-purple-700">
                    <Save className="w-4 h-4 mr-2" />
                    Save Changes
                  </Button>
                </CardContent>
              </Card>
            )}

            {activeTab === 'security' && (
              <Card className="bg-gray-800/50 border-gray-700">
                <CardHeader>
                  <CardTitle className="text-white">Security Settings</CardTitle>
                  <CardDescription className="text-gray-400">
                    Manage your password and security preferences
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-4">
                    <h3 className="text-lg text-white">Change Password</h3>
                    <div className="space-y-2">
                      <label className="text-sm text-gray-300">Current Password</label>
                      <Input
                        type="password"
                        className="bg-gray-900/50 border-gray-700 text-white"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm text-gray-300">New Password</label>
                      <Input
                        type="password"
                        className="bg-gray-900/50 border-gray-700 text-white"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm text-gray-300">Confirm New Password</label>
                      <Input
                        type="password"
                        className="bg-gray-900/50 border-gray-700 text-white"
                      />
                    </div>
                    <Button className="bg-purple-600 hover:bg-purple-700">
                      Update Password
                    </Button>
                  </div>

                  <div className="border-t border-gray-700 pt-6">
                    <h3 className="text-lg text-white mb-4">Two-Factor Authentication</h3>
                    <p className="text-gray-400 mb-4">
                      Add an extra layer of security to your account
                    </p>
                    <Button variant="outline" className="border-gray-700 text-gray-300">
                      Enable 2FA
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {activeTab === 'api-keys' && (
              <Card className="bg-gray-800/50 border-gray-700">
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-white">API Keys</CardTitle>
                    <CardDescription className="text-gray-400">
                      Manage your API keys for programmatic access
                    </CardDescription>
                  </div>
                  <Button className="bg-purple-600 hover:bg-purple-700">
                    <Plus className="w-4 h-4 mr-2" />
                    Create Key
                  </Button>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {apiKeys.map((key) => (
                      <div
                        key={key.id}
                        className="flex items-center justify-between p-4 bg-gray-900/50 rounded-lg"
                      >
                        <div>
                          <p className="text-white font-medium">{key.name}</p>
                          <div className="flex items-center space-x-2 mt-1">
                            <code className="text-sm text-gray-400">
                              {showApiKey ? `${key.prefix}xxxxxxxxxxxxxxxx` : '••••••••••••••••'}
                            </code>
                            <button
                              onClick={() => setShowApiKey(!showApiKey)}
                              className="text-gray-500 hover:text-gray-300"
                            >
                              {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                            </button>
                            <button className="text-gray-500 hover:text-gray-300">
                              <Copy className="w-4 h-4" />
                            </button>
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            Created {key.created} • Last used {key.lastUsed}
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {activeTab === 'billing' && (
              <Card className="bg-gray-800/50 border-gray-700">
                <CardHeader>
                  <CardTitle className="text-white">Billing & Subscription</CardTitle>
                  <CardDescription className="text-gray-400">
                    Manage your subscription and payment methods
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-purple-400 font-medium">Pro Plan</p>
                        <p className="text-sm text-gray-400">$29/month • Renews Jan 20, 2024</p>
                      </div>
                      <Button variant="outline" className="border-purple-500 text-purple-400">
                        Manage Plan
                      </Button>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-lg text-white mb-4">Payment Method</h3>
                    <div className="flex items-center justify-between p-4 bg-gray-900/50 rounded-lg">
                      <div className="flex items-center space-x-4">
                        <div className="w-12 h-8 bg-gradient-to-r from-blue-600 to-blue-400 rounded flex items-center justify-center text-white text-xs font-bold">
                          VISA
                        </div>
                        <div>
                          <p className="text-white">•••• •••• •••• 4242</p>
                          <p className="text-sm text-gray-400">Expires 12/25</p>
                        </div>
                      </div>
                      <Button variant="outline" className="border-gray-700 text-gray-300">
                        Update
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {activeTab === 'notifications' && (
              <Card className="bg-gray-800/50 border-gray-700">
                <CardHeader>
                  <CardTitle className="text-white">Notification Preferences</CardTitle>
                  <CardDescription className="text-gray-400">
                    Choose how you want to be notified
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {[
                    { title: 'Identity Matches', desc: 'When your identity is detected in content' },
                    { title: 'License Requests', desc: 'When someone requests to license your identity' },
                    { title: 'Payment Received', desc: 'When you receive a payment' },
                    { title: 'Weekly Reports', desc: 'Summary of your identity activity' },
                    { title: 'Marketing', desc: 'News and updates from ActorHub.ai' },
                  ].map((item, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <div>
                        <p className="text-white">{item.title}</p>
                        <p className="text-sm text-gray-400">{item.desc}</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input type="checkbox" defaultChecked={index < 4} className="sr-only peer" />
                        <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                      </label>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

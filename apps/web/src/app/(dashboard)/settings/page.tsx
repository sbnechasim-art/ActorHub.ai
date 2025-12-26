'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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
  Loader2,
  AlertCircle,
  Check,
  ExternalLink,
  QrCode,
} from 'lucide-react'
import { userApi, notificationsApi, subscriptionsApi, twoFactorApi } from '@/lib/api'
import { logger } from '@/lib/logger'

interface ApiKey {
  id: string
  name: string
  key_prefix: string  // Matches backend field name
  permissions: string[]
  rate_limit: number
  is_active: boolean
  usage_count: number
  last_used_at: string | null
  expires_at: string | null
  created_at: string
}

interface UserProfile {
  id: string
  email: string
  first_name?: string
  last_name?: string
  display_name?: string
  avatar_url?: string
}

interface NotificationPreferences {
  identity_matches: boolean
  license_requests: boolean
  payment_received: boolean
  weekly_reports: boolean
  marketing: boolean
}

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('profile')
  const [showApiKey, setShowApiKey] = useState<Record<string, boolean>>({})
  const [newKeyName, setNewKeyName] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null)
  const [deletingKeyId, setDeletingKeyId] = useState<string | null>(null)

  // Profile state
  const [profile, setProfile] = useState({
    firstName: '',
    lastName: '',
    email: '',
    displayName: '',
  })
  const [profileDirty, setProfileDirty] = useState(false)

  // Password state
  const [passwords, setPasswords] = useState({
    current: '',
    new: '',
    confirm: '',
  })
  const [passwordError, setPasswordError] = useState<string | null>(null)

  // 2FA state
  const [show2FASetup, setShow2FASetup] = useState(false)
  const [twoFACode, setTwoFACode] = useState('')
  const [twoFASecret, setTwoFASecret] = useState<{ secret: string; qr_code: string; backup_codes: string[] } | null>(null)

  // Notification preferences state
  const [notifPrefs, setNotifPrefs] = useState<NotificationPreferences>({
    identity_matches: true,
    license_requests: true,
    payment_received: true,
    weekly_reports: true,
    marketing: false,
  })

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'billing', label: 'Billing', icon: CreditCard },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'api-keys', label: 'API Keys', icon: Key },
  ]

  // Fetch user profile
  const { data: userData, isLoading: isLoadingUser } = useQuery({
    queryKey: ['user-profile'],
    queryFn: userApi.getMe,
    enabled: activeTab === 'profile',
  })

  // Update profile when data loads
  useEffect(() => {
    if (userData) {
      setProfile({
        firstName: userData.first_name || '',
        lastName: userData.last_name || '',
        email: userData.email || '',
        displayName: userData.display_name || '',
      })
    }
  }, [userData])

  // Fetch subscription info
  const { data: subscriptionData, isLoading: isLoadingSubscription } = useQuery({
    queryKey: ['subscription'],
    queryFn: subscriptionsApi.getCurrent,
    enabled: activeTab === 'billing',
  })

  // Fetch notification preferences
  const { data: notifData, isLoading: isLoadingNotifs } = useQuery({
    queryKey: ['notification-preferences'],
    queryFn: notificationsApi.getPreferences,
    enabled: activeTab === 'notifications',
  })

  // Update notification state when data loads
  useEffect(() => {
    if (notifData) {
      setNotifPrefs(notifData)
    }
  }, [notifData])

  // Fetch API keys
  const { data: apiKeys = [], isLoading: isLoadingKeys, error: keysError } = useQuery<ApiKey[]>({
    queryKey: ['api-keys'],
    queryFn: userApi.getApiKeys,
    enabled: activeTab === 'api-keys',
  })

  // Save profile mutation
  const saveProfileMutation = useMutation({
    mutationFn: (data: { first_name?: string; last_name?: string; display_name?: string }) =>
      userApi.updateMe(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-profile'] })
      setProfileDirty(false)
    },
  })

  // Change password mutation
  const changePasswordMutation = useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) =>
      userApi.updateMe(data),
    onSuccess: () => {
      setPasswords({ current: '', new: '', confirm: '' })
      setPasswordError(null)
    },
    onError: (error: any) => {
      setPasswordError(error.response?.data?.detail || 'Failed to change password')
    },
  })

  // Enable 2FA mutation
  const enable2FAMutation = useMutation({
    mutationFn: twoFactorApi.enable,
    onSuccess: (data) => {
      setTwoFASecret(data)
      setShow2FASetup(true)
    },
    onError: (error: Error) => {
      console.error('Failed to enable 2FA:', error.message)
    },
  })

  // Verify 2FA mutation
  const verify2FAMutation = useMutation({
    mutationFn: twoFactorApi.verify,
    onSuccess: () => {
      setShow2FASetup(false)
      setTwoFACode('')
      setTwoFASecret(null)
      queryClient.invalidateQueries({ queryKey: ['user-profile'] })
    },
    onError: (error: Error) => {
      console.error('Failed to verify 2FA code:', error.message)
    },
  })

  // Update notification preferences mutation
  const updateNotifMutation = useMutation({
    mutationFn: (prefs: NotificationPreferences) => notificationsApi.updatePreferences(prefs),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-preferences'] })
    },
  })

  // Create API key mutation
  const createKeyMutation = useMutation({
    mutationFn: (name: string) => userApi.createApiKey({ name }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      setNewKeyName('')
      setShowCreateForm(false)
      // Store newly created key to show it once
      // Backend returns { api_key: "ah_xxx...", key_info: {...} }
      if (data.api_key) {
        setNewlyCreatedKey(data.api_key)
      }
    },
  })

  // Revoke API key mutation
  const revokeKeyMutation = useMutation({
    mutationFn: (id: string) => {
      setDeletingKeyId(id)
      return userApi.revokeApiKey(id)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      setDeletingKeyId(null)
    },
    onError: (error: any) => {
      logger.error('Failed to revoke API key', error)
      setDeletingKeyId(null)
    },
  })

  // Manage subscription mutation (opens Stripe portal)
  const manageSubscriptionMutation = useMutation({
    mutationFn: subscriptionsApi.getPortalUrl,
    onSuccess: (data) => {
      if (data.url) {
        window.open(data.url, '_blank')
      }
    },
    onError: (error: Error) => {
      console.error('Failed to open subscription portal:', error.message)
    },
  })

  const handleCreateKey = () => {
    if (newKeyName.trim()) {
      createKeyMutation.mutate(newKeyName.trim())
    }
  }

  const handleSaveProfile = () => {
    saveProfileMutation.mutate({
      first_name: profile.firstName,
      last_name: profile.lastName,
      display_name: profile.displayName,
    })
  }

  const handleChangePassword = () => {
    setPasswordError(null)
    if (passwords.new !== passwords.confirm) {
      setPasswordError('Passwords do not match')
      return
    }
    if (passwords.new.length < 8) {
      setPasswordError('Password must be at least 8 characters')
      return
    }
    changePasswordMutation.mutate({
      current_password: passwords.current,
      new_password: passwords.new,
    })
  }

  const handleNotificationChange = (key: keyof NotificationPreferences, value: boolean) => {
    const newPrefs = { ...notifPrefs, [key]: value }
    setNotifPrefs(newPrefs)
    updateNotifMutation.mutate(newPrefs)
  }

  const copyToClipboard = async (text: string, keyId: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedKey(keyId)
      setTimeout(() => setCopiedKey(null), 2000)
    } catch (err) {
      logger.error('Failed to copy to clipboard', err as Error)
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never'
    return new Date(dateString).toLocaleDateString()
  }

  const getInitials = () => {
    const first = profile.firstName?.[0] || ''
    const last = profile.lastName?.[0] || ''
    return (first + last).toUpperCase() || 'U'
  }

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
                  {isLoadingUser ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-purple-500" />
                    </div>
                  ) : (
                    <>
                      <div className="flex items-center space-x-6">
                        <div className="w-24 h-24 bg-purple-600 rounded-full flex items-center justify-center text-3xl text-white">
                          {getInitials()}
                        </div>
                        <Button variant="outline" className="border-gray-700 text-gray-300">
                          Change Avatar
                        </Button>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <label className="text-sm text-gray-300">First Name</label>
                          <Input
                            value={profile.firstName}
                            onChange={(e) => {
                              setProfile({ ...profile, firstName: e.target.value })
                              setProfileDirty(true)
                            }}
                            className="bg-gray-900/50 border-gray-700 text-white"
                          />
                        </div>
                        <div className="space-y-2">
                          <label className="text-sm text-gray-300">Last Name</label>
                          <Input
                            value={profile.lastName}
                            onChange={(e) => {
                              setProfile({ ...profile, lastName: e.target.value })
                              setProfileDirty(true)
                            }}
                            className="bg-gray-900/50 border-gray-700 text-white"
                          />
                        </div>
                      </div>

                      <div className="space-y-2">
                        <label className="text-sm text-gray-300">Email</label>
                        <Input
                          type="email"
                          value={profile.email}
                          disabled
                          className="bg-gray-900/50 border-gray-700 text-gray-500"
                        />
                        <p className="text-xs text-gray-500">Email cannot be changed</p>
                      </div>

                      <div className="space-y-2">
                        <label className="text-sm text-gray-300">Display Name</label>
                        <Input
                          value={profile.displayName}
                          onChange={(e) => {
                            setProfile({ ...profile, displayName: e.target.value })
                            setProfileDirty(true)
                          }}
                          className="bg-gray-900/50 border-gray-700 text-white"
                        />
                      </div>

                      <Button
                        className="bg-purple-600 hover:bg-purple-700"
                        onClick={handleSaveProfile}
                        disabled={!profileDirty || saveProfileMutation.isPending}
                      >
                        {saveProfileMutation.isPending ? (
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        ) : saveProfileMutation.isSuccess ? (
                          <Check className="w-4 h-4 mr-2" />
                        ) : (
                          <Save className="w-4 h-4 mr-2" />
                        )}
                        {saveProfileMutation.isSuccess ? 'Saved!' : 'Save Changes'}
                      </Button>
                    </>
                  )}
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
                        value={passwords.current}
                        onChange={(e) => setPasswords({ ...passwords, current: e.target.value })}
                        className="bg-gray-900/50 border-gray-700 text-white"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm text-gray-300">New Password</label>
                      <Input
                        type="password"
                        value={passwords.new}
                        onChange={(e) => setPasswords({ ...passwords, new: e.target.value })}
                        className="bg-gray-900/50 border-gray-700 text-white"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm text-gray-300">Confirm New Password</label>
                      <Input
                        type="password"
                        value={passwords.confirm}
                        onChange={(e) => setPasswords({ ...passwords, confirm: e.target.value })}
                        className="bg-gray-900/50 border-gray-700 text-white"
                      />
                    </div>
                    {passwordError && (
                      <p className="text-red-400 text-sm">{passwordError}</p>
                    )}
                    {changePasswordMutation.isSuccess && (
                      <p className="text-green-400 text-sm">Password changed successfully!</p>
                    )}
                    <Button
                      className="bg-purple-600 hover:bg-purple-700"
                      onClick={handleChangePassword}
                      disabled={!passwords.current || !passwords.new || !passwords.confirm || changePasswordMutation.isPending}
                    >
                      {changePasswordMutation.isPending ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        'Update Password'
                      )}
                    </Button>
                  </div>

                  <div className="border-t border-gray-700 pt-6">
                    <h3 className="text-lg text-white mb-4">Two-Factor Authentication</h3>
                    <p className="text-gray-400 mb-4">
                      Add an extra layer of security to your account
                    </p>

                    {show2FASetup && twoFASecret ? (
                      <div className="space-y-4 p-4 bg-gray-900/50 rounded-lg border border-gray-700">
                        <div className="flex justify-center">
                          <img src={twoFASecret.qr_code} alt="2FA QR Code" className="w-48 h-48" />
                        </div>
                        <p className="text-sm text-gray-400 text-center">
                          Scan this QR code with your authenticator app
                        </p>
                        <div className="text-center">
                          <p className="text-xs text-gray-500 mb-1">Or enter this code manually:</p>
                          <code className="text-purple-400 bg-gray-800 px-3 py-1 rounded">
                            {twoFASecret.secret}
                          </code>
                        </div>
                        <div className="space-y-2">
                          <label className="text-sm text-gray-300">Enter verification code</label>
                          <Input
                            value={twoFACode}
                            onChange={(e) => setTwoFACode(e.target.value)}
                            placeholder="000000"
                            maxLength={6}
                            className="bg-gray-800 border-gray-600 text-white text-center text-2xl tracking-widest"
                          />
                        </div>
                        <div className="flex gap-3">
                          <Button
                            variant="outline"
                            className="flex-1 border-gray-600"
                            onClick={() => {
                              setShow2FASetup(false)
                              setTwoFASecret(null)
                              setTwoFACode('')
                            }}
                          >
                            Cancel
                          </Button>
                          <Button
                            className="flex-1 bg-purple-600 hover:bg-purple-700"
                            onClick={() => verify2FAMutation.mutate(twoFACode)}
                            disabled={twoFACode.length !== 6 || verify2FAMutation.isPending}
                          >
                            {verify2FAMutation.isPending ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              'Verify & Enable'
                            )}
                          </Button>
                        </div>
                        {twoFASecret.backup_codes && (
                          <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                            <p className="text-yellow-400 text-sm font-medium mb-2">Save your backup codes:</p>
                            <div className="grid grid-cols-2 gap-2">
                              {twoFASecret.backup_codes.map((code, i) => (
                                <code key={i} className="text-xs text-gray-300 bg-gray-800 px-2 py-1 rounded">
                                  {code}
                                </code>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <Button
                        variant="outline"
                        className="border-gray-700 text-gray-300"
                        onClick={() => enable2FAMutation.mutate()}
                        disabled={enable2FAMutation.isPending}
                      >
                        {enable2FAMutation.isPending ? (
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        ) : (
                          <QrCode className="w-4 h-4 mr-2" />
                        )}
                        Enable 2FA
                      </Button>
                    )}
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
                  <Button
                    className="bg-purple-600 hover:bg-purple-700"
                    onClick={() => setShowCreateForm(true)}
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Create Key
                  </Button>
                </CardHeader>
                <CardContent>
                  {/* Newly Created Key Alert */}
                  {newlyCreatedKey && (
                    <div className="mb-6 p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
                      <p className="text-green-400 font-medium mb-2">API Key Created!</p>
                      <p className="text-gray-400 text-sm mb-3">
                        Copy this key now. You won't be able to see it again.
                      </p>
                      <div className="flex gap-2">
                        <code className="flex-1 text-sm text-green-300 bg-gray-900 px-3 py-2 rounded font-mono overflow-x-auto">
                          {newlyCreatedKey}
                        </code>
                        <Button
                          size="sm"
                          onClick={() => {
                            copyToClipboard(newlyCreatedKey, 'new')
                            setNewlyCreatedKey(null)
                          }}
                          className="bg-green-600 hover:bg-green-700"
                        >
                          {copiedKey === 'new' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                        </Button>
                      </div>
                    </div>
                  )}

                  {/* Create Key Form */}
                  {showCreateForm && (
                    <div className="mb-6 p-4 bg-gray-900/50 rounded-lg border border-gray-700">
                      <p className="text-white font-medium mb-3">Create New API Key</p>
                      <div className="flex gap-3">
                        <Input
                          placeholder="Key name (e.g., Production, Development)"
                          value={newKeyName}
                          onChange={(e) => setNewKeyName(e.target.value)}
                          className="flex-1 bg-gray-800 border-gray-600 text-white"
                        />
                        <Button
                          onClick={handleCreateKey}
                          disabled={!newKeyName.trim() || createKeyMutation.isPending}
                          className="bg-purple-600 hover:bg-purple-700"
                        >
                          {createKeyMutation.isPending ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            'Create'
                          )}
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => {
                            setShowCreateForm(false)
                            setNewKeyName('')
                          }}
                          className="border-gray-600"
                        >
                          Cancel
                        </Button>
                      </div>
                      {createKeyMutation.isError && (
                        <p className="text-red-400 text-sm mt-2">
                          Failed to create API key. Please try again.
                        </p>
                      )}
                    </div>
                  )}

                  {/* Loading State */}
                  {isLoadingKeys && (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-purple-500" />
                    </div>
                  )}

                  {/* Error State */}
                  {keysError && (
                    <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                      <AlertCircle className="w-5 h-5 text-red-400" />
                      <p className="text-red-400">Failed to load API keys</p>
                    </div>
                  )}

                  {/* Empty State */}
                  {!isLoadingKeys && !keysError && apiKeys.length === 0 && (
                    <div className="text-center py-8">
                      <Key className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                      <p className="text-gray-400">No API keys yet</p>
                      <p className="text-gray-500 text-sm">Create your first API key to get started</p>
                    </div>
                  )}

                  {/* API Keys List */}
                  {!isLoadingKeys && !keysError && apiKeys.length > 0 && (
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
                                {showApiKey[key.id] ? `${key.key_prefix}••••••••••••••••••••••••••••••••` : '••••••••••••••••••••••••••••••••••••••••'}
                              </code>
                              <button
                                onClick={() => setShowApiKey({ ...showApiKey, [key.id]: !showApiKey[key.id] })}
                                className="text-gray-500 hover:text-gray-300"
                                aria-label={showApiKey[key.id] ? 'Hide API key' : 'Show API key'}
                              >
                                {showApiKey[key.id] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                              </button>
                              <button
                                onClick={() => copyToClipboard(key.key_prefix, key.id)}
                                className="text-gray-500 hover:text-gray-300"
                                title="Copy key prefix (full key only shown at creation)"
                                aria-label="Copy API key prefix"
                              >
                                {copiedKey === key.id ? (
                                  <Check className="w-4 h-4 text-green-400" />
                                ) : (
                                  <Copy className="w-4 h-4" />
                                )}
                              </button>
                            </div>
                            <p className="text-xs text-gray-500 mt-1">
                              Created {formatDate(key.created_at)} •
                              {key.usage_count > 0 ? ` ${key.usage_count} uses • Last used ${formatDate(key.last_used_at)}` : ' Never used'}
                            </p>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                            onClick={() => {
                              if (confirm(`Are you sure you want to revoke the API key "${key.name}"? This cannot be undone.`)) {
                                revokeKeyMutation.mutate(key.id)
                              }
                            }}
                            disabled={deletingKeyId === key.id}
                            aria-label={`Revoke ${key.name}`}
                          >
                            {deletingKeyId === key.id ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Trash2 className="w-4 h-4" />
                            )}
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
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
                  {isLoadingSubscription ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-purple-500" />
                    </div>
                  ) : (
                    <>
                      <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-purple-400 font-medium">
                              {subscriptionData?.plan?.name || 'Free'} Plan
                            </p>
                            <p className="text-sm text-gray-400">
                              {subscriptionData?.plan?.price
                                ? `$${subscriptionData.plan.price}/${subscriptionData.plan.interval}`
                                : 'No active subscription'}
                              {subscriptionData?.current_period_end && (
                                <> • Renews {new Date(subscriptionData.current_period_end).toLocaleDateString()}</>
                              )}
                            </p>
                          </div>
                          <Button
                            variant="outline"
                            className="border-purple-500 text-purple-400"
                            onClick={() => manageSubscriptionMutation.mutate()}
                            disabled={manageSubscriptionMutation.isPending}
                          >
                            {manageSubscriptionMutation.isPending ? (
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            ) : (
                              <ExternalLink className="w-4 h-4 mr-2" />
                            )}
                            Manage Plan
                          </Button>
                        </div>
                      </div>

                      <div>
                        <h3 className="text-lg text-white mb-4">Payment Method</h3>
                        <div className="flex items-center justify-between p-4 bg-gray-900/50 rounded-lg">
                          <div className="flex items-center space-x-4">
                            <div className="w-12 h-8 bg-gradient-to-r from-blue-600 to-blue-400 rounded flex items-center justify-center text-white text-xs font-bold">
                              {subscriptionData?.payment_method?.brand?.toUpperCase() || 'CARD'}
                            </div>
                            <div>
                              <p className="text-white">
                                •••• •••• •••• {subscriptionData?.payment_method?.last4 || '****'}
                              </p>
                              <p className="text-sm text-gray-400">
                                Expires {subscriptionData?.payment_method?.exp_month || '--'}/{subscriptionData?.payment_method?.exp_year || '--'}
                              </p>
                            </div>
                          </div>
                          <Button
                            variant="outline"
                            className="border-gray-700 text-gray-300"
                            onClick={() => manageSubscriptionMutation.mutate()}
                            disabled={manageSubscriptionMutation.isPending}
                          >
                            {manageSubscriptionMutation.isPending ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              'Update'
                            )}
                          </Button>
                        </div>
                      </div>
                    </>
                  )}
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
                  {isLoadingNotifs ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-purple-500" />
                    </div>
                  ) : (
                    <>
                      {[
                        { key: 'identity_matches', title: 'Identity Matches', desc: 'When your identity is detected in content' },
                        { key: 'license_requests', title: 'License Requests', desc: 'When someone requests to license your identity' },
                        { key: 'payment_received', title: 'Payment Received', desc: 'When you receive a payment' },
                        { key: 'weekly_reports', title: 'Weekly Reports', desc: 'Summary of your identity activity' },
                        { key: 'marketing', title: 'Marketing', desc: 'News and updates from ActorHub.ai' },
                      ].map((item) => (
                        <div key={item.key} className="flex items-center justify-between">
                          <div>
                            <label htmlFor={item.key} className="text-white cursor-pointer">{item.title}</label>
                            <p className="text-sm text-gray-400">{item.desc}</p>
                          </div>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              id={item.key}
                              checked={notifPrefs[item.key as keyof NotificationPreferences]}
                              onChange={(e) => handleNotificationChange(item.key as keyof NotificationPreferences, e.target.checked)}
                              className="sr-only peer"
                              role="switch"
                              aria-label={`${item.title} notification toggle`}
                            />
                            <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-purple-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                          </label>
                        </div>
                      ))}
                      {updateNotifMutation.isPending && (
                        <p className="text-gray-400 text-sm flex items-center gap-2">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Saving...
                        </p>
                      )}
                    </>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

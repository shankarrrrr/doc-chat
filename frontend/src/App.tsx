import { useEffect, useMemo, useState, useRef } from 'react'
import type { Session } from '@supabase/supabase-js'
import './App.css'
import { supabase } from './lib/supabaseClient'
import { HealthQuestionnaire, type HealthOnboardingPayload } from './components/MultiStepOnboarding'
import { RecordsPage } from './components/RecordsPage'
import { OverviewPage } from './components/OverviewPage'
import { normalizeOnboardingData } from './lib/healthInsights'
import { DoctorPortal } from './components/DoctorPortal'

type BackendMe = {
  user: {
    id: string
    email: string | null
    name: string | null
  }
  profile: {
    onboarding_completed: boolean
    onboarding_data: Record<string, unknown>
    health_summary: string
  }
}

async function readJson(res: Response): Promise<unknown> {
  try {
    return await res.json()
  } catch {
    return null
  }
}

function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message
  return String(err)
}



function App() {
  const apiUrl = import.meta.env.VITE_API_URL as string | undefined

  // Check if we're on the /doctor route
  const isDoctorRoute = window.location.pathname === '/doctor' || window.location.pathname === '/doctor/'

  // If on doctor route, render doctor portal
  if (isDoctorRoute) {
    return <DoctorPortal apiUrl={apiUrl} />
  }

  return <PatientApp apiUrl={apiUrl} />
}

function PatientApp({ apiUrl }: { apiUrl: string | undefined }) {
  const [authLoading, setAuthLoading] = useState(true)
  const [meLoading, setMeLoading] = useState(false)
  const [session, setSession] = useState<Session | null>(null)
  const [me, setMe] = useState<BackendMe | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'records' | 'care'>('overview')
  const [chatOpen, setChatOpen] = useState(true)
  const [showDocUpload, setShowDocUpload] = useState(false)
  const [uploadingDoc, setUploadingDoc] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const accessToken = session?.access_token ?? null

  const needsOnboarding = useMemo(() => {
    if (!session || !me) return false
    const data = me.profile.onboarding_data || {}
    const hasData = Object.keys(data).length > 0
    const completed = me.profile.onboarding_completed === true && hasData
    return !completed
  }, [me, session])

  const onboardingData = useMemo(() => {
    if (!me) return null
    return normalizeOnboardingData(me.profile.onboarding_data)
  }, [me])


    useEffect(() => {
    let cancelled = false

    supabase.auth
      .getSession()
      .then(({ data, error }) => {
        if (cancelled) return
        if (error) {
          setError(error.message)
          setSession(null)
          return
        }
        setSession(data.session)
      })
      .finally(() => {
        if (cancelled) return
        setAuthLoading(false)
      })

    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
    })

    return () => {
      cancelled = true
      data.subscription.unsubscribe()
    }
  }, [])

  useEffect(() => {
    if (!apiUrl) return
    if (!accessToken) {
      setMe(null)
      return
    }

    const controller = new AbortController()
    setMeLoading(true)
    setError(null)

    fetch(`${apiUrl}/api/me/`, {
      signal: controller.signal,
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    })
      .then(async (res) => {
        const body = await readJson(res)
        if (!res.ok) {
          const message =
            body && typeof body === 'object' && 'detail' in body
              ? String((body as { detail: unknown }).detail)
              : `HTTP ${res.status}`
          throw new Error(message)
        }
        return body
      })
      .then((body) => {
        setMe(body as BackendMe)
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === 'AbortError') return
        setError(getErrorMessage(err))
      })
      .finally(() => setMeLoading(false))

    return () => controller.abort()
  }, [accessToken, apiUrl])

  async function signInWithGoogle() {
    setError(null)
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: window.location.origin,
        queryParams: {
          prompt: 'select_account',
        },
      },
    })
    if (error) setError(error.message)
  }

  async function signOut() {
    setError(null)
    const { error } = await supabase.auth.signOut()
    if (error) setError(error.message)
  }

  async function handleDocumentUpload(files: FileList | null) {
    if (!files || files.length === 0 || !apiUrl || !accessToken) return

    setUploadingDoc(true)
    setUploadError(null)

    const formData = new FormData()
    for (let i = 0; i < files.length; i++) {
      formData.append('documents', files[i])
    }

    try {
      const res = await fetch(`${apiUrl}/api/parse-documents/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      })
      const body = await readJson(res)
      if (!res.ok) {
        const message =
          body && typeof body === 'object' && 'detail' in body
            ? String((body as { detail: unknown }).detail)
            : `HTTP ${res.status}`
        throw new Error(message)
      }
      setMe(body as BackendMe)
      setShowDocUpload(false)
    } catch (err) {
      setUploadError(getErrorMessage(err))
    } finally {
      setUploadingDoc(false)
    }
  }

  async function submitOnboarding(payload: HealthOnboardingPayload) {
    if (!apiUrl) throw new Error('Missing VITE_API_URL')
    if (!accessToken) throw new Error('Not authenticated')

    setMeLoading(true)
    setError(null)

    try {
      const res = await fetch(`${apiUrl}/api/onboarding/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })
      const body = await readJson(res)
      if (!res.ok) {
        const message =
          body && typeof body === 'object' && 'detail' in body
            ? String((body as { detail: unknown }).detail)
            : `HTTP ${res.status}`
        throw new Error(message)
      }
      setMe(body as BackendMe)
    } finally {
      setMeLoading(false)
    }
  }

  if (authLoading) {
    return (
      <div className="page">
        <div className="header">
          <div className="brand">
            <h1>AI Doctor</h1>
            <p>Personalized care, powered by you.</p>
          </div>
        </div>
        <div className="card">
          <p style={{ margin: 0, color: '#475569' }}>Loadingâ€¦</p>
        </div>
      </div>
    )
  }

  if (!session) {
    return (
      <div className="login-page">
        <div className="login-background">
          <div className="login-gradient-orb login-orb-1"></div>
          <div className="login-gradient-orb login-orb-2"></div>
          <div className="login-gradient-orb login-orb-3"></div>
        </div>
        <div className="login-container">
          <div className="login-card">
            <div className="login-header">
              <div className="login-logo">
                <span className="login-logo-icon">🩺</span>
              </div>
              <h1 className="login-title">AI Doctor</h1>
              <p className="login-tagline">Fast, private and secure.</p>
            </div>
            <div className="login-divider">
              <span>Get Started</span>
            </div>
            <div className="login-content">
              <p className="login-description">
                Your personal AI health assistant. Get personalized health insights, track your wellness, and receive expert guidance.
              </p>
              {error ? <p className="error">{error}</p> : null}
              <button onClick={signInWithGoogle} className="login-google-btn">
                <svg className="google-icon" viewBox="0 0 24 24" width="20" height="20">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Continue with Google
              </button>
            </div>
            <div className="login-footer">
              <p>By continuing, you agree to our Terms of Service and Privacy Policy</p>
            </div>
          </div>
          <div className="login-features">
            <div className="login-feature animate-fadeInUp" style={{ animationDelay: '0.1s' }}>
              <span className="login-feature-icon">🔒</span>
              <div>
                <h4>Private & Secure</h4>
                <p>Your health data is encrypted and protected</p>
              </div>
            </div>
            <div className="login-feature animate-fadeInUp" style={{ animationDelay: '0.2s' }}>
              <span className="login-feature-icon">⚡</span>
              <div>
                <h4>Instant Insights</h4>
                <p>Get personalized health recommendations</p>
              </div>
            </div>
            <div className="login-feature animate-fadeInUp" style={{ animationDelay: '0.3s' }}>
              <span className="login-feature-icon">📋</span>
              <div>
                <h4>Track Records</h4>
                <p>Upload and manage your medical documents</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (meLoading && !me) {
    return (
      <div className="page">
        <div className="header">
          <div className="brand">
            <h1>AI Doctor</h1>
            <p>Personalized care, powered by you.</p>
          </div>
          <button onClick={signOut} className="secondary-btn">Sign out</button>
        </div>
        <div className="card">
          <p style={{ margin: 0, color: '#475569' }}>Loading profileâ€¦</p>
        </div>
      </div>
    )
  }

  if (!me) {
    return (
      <div className="page">
        <div className="header">
          <div className="brand">
            <h1>AI Doctor</h1>
            <p>Personalized care, powered by you.</p>
          </div>
          <button onClick={signOut} className="secondary-btn">Sign out</button>
        </div>
        <div className="card">
          <p className="error" style={{ margin: 0 }}>{error ?? 'Failed to load profile'}</p>
        </div>
      </div>
    )
  }

  if (needsOnboarding) {
    return (
      <div className="app-shell">
        <div className="top-nav">
          <div className="brand">
            <h1>Health questionnaire</h1>
            <p>Two quick steps to tailor your care.</p>
          </div>
          <div className="top-nav-actions">
            <button onClick={signOut} className="secondary-btn">Sign out</button>
          </div>
        </div>

        <div className="onboarding-content">
          <div className="page page-surface onboarding-page">
            <HealthQuestionnaire
              initialFullName={me.user.name ?? ''}
              onSubmit={submitOnboarding}
              disabled={meLoading}
              accessToken={accessToken}
              apiUrl={apiUrl}
            />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <div className="top-nav">
        <div className="brand">
          <h1>AI Care Hub</h1>
          <p>Smart hospital-inspired experience.</p>
        </div>
        <div className="top-nav-actions">
          <div className="nav-bar">
            {[
              { id: 'overview', label: 'Overview' },
              { id: 'records', label: 'Records' },
            ].map((tab) => (
              <button
                key={tab.id}
                className={`nav-tab ${activeTab === tab.id ? 'nav-tab-active' : ''}`}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <button onClick={signOut} className="secondary-btn">Sign out</button>
        </div>
      </div>

      <div className={`content-with-chat ${activeTab !== 'overview' ? 'chat-hidden' : ''}`}>
        <div className="page page-surface">
          {!onboardingData ? (
            <div className="card card-stack">
              <span className="pill">Account</span>
              <div className="text-stack">
                <p className="account-email">{me.user.email ?? 'Unknown email'}</p>
                <p className="account-status">Loading your profileâ€¦</p>
              </div>
              {error ? <p className="error">{error}</p> : null}
            </div>
          ) : (
            <>
              {showDocUpload && (
                <DocumentUploadModal
                  onClose={() => setShowDocUpload(false)}
                  onUpload={handleDocumentUpload}
                  uploading={uploadingDoc}
                  error={uploadError}
                  accessToken={accessToken}
                  apiUrl={apiUrl}
                  onProfileUpdate={(healthSummary) => {
                    setMe(prev => prev ? {...prev, profile: {...prev.profile, health_summary: healthSummary}} : prev)
                  }}
                />
              )}

              {activeTab === 'overview' && (
                <OverviewPage
                  onboardingData={onboardingData}
                  healthSummary={me.profile.health_summary}
                  onAddDocuments={() => setShowDocUpload(true)}
                  onViewRecords={() => setActiveTab('records')}
                  onOpenChat={() => setChatOpen(true)}
                  accessToken={accessToken}
                  apiUrl={apiUrl}
                />
              )}

              {activeTab === 'records' && (
                <RecordsPage
                  onboardingData={onboardingData}
                  healthSummary={me.profile.health_summary}
                  onAddDocuments={() => setShowDocUpload(true)}
                  onConsultDoctor={() => setActiveTab('overview')}
                  accessToken={accessToken}
                  apiUrl={apiUrl}
                />
              )}


            </>
          )}
        </div>

        {activeTab === 'overview' && (
          <ChatPanel open={chatOpen} onToggle={() => setChatOpen((v) => !v)} accessToken={accessToken} apiUrl={apiUrl} />
        )}
      </div>
    </div>
  )
}

type ChatMessageType = {
  id: number
  role: 'ai' | 'user'
  content: string
  created_at: string
}

type ChatSessionType = {
  id: number
  title: string
  created_at: string
  updated_at: string
}

function ChatPanel({ open, onToggle, accessToken, apiUrl }: { open: boolean; onToggle: () => void; accessToken: string | null; apiUrl: string | undefined }) {
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [sessions, setSessions] = useState<ChatSessionType[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null)
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (accessToken && apiUrl) {
      fetchSessions()
    }
  }, [accessToken, apiUrl])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function fetchSessions() {
    if (!apiUrl || !accessToken) return
    try {
      const res = await fetch(`${apiUrl}/api/chat/sessions/`, {
        headers: { Authorization: `Bearer ${accessToken}` }
      })
      if (res.ok) {
        const data = await res.json()
        setSessions(data.sessions || [])
      }
    } catch (e) {
      console.error('Failed to fetch sessions:', e)
    }
  }

  async function createSession(): Promise<number | null> {
    if (!apiUrl || !accessToken) return null
    try {
      const res = await fetch(`${apiUrl}/api/chat/sessions/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
      })
      if (res.ok) {
        const data = await res.json()
        setCurrentSessionId(data.id)
        fetchSessions()
        return data.id
      }
    } catch (e) {
      console.error('Failed to create session:', e)
    }
    return null
  }

  async function loadSession(sessionId: number) {
    if (!apiUrl || !accessToken) return
    try {
      const res = await fetch(`${apiUrl}/api/chat/sessions/${sessionId}/`, {
        headers: { Authorization: `Bearer ${accessToken}` }
      })
      if (res.ok) {
        const data = await res.json()
        setMessages(data.messages || [])
        setCurrentSessionId(sessionId)
        setShowHistory(false)
      }
    } catch (e) {
      console.error('Failed to load session:', e)
    }
  }

  async function sendMessage() {
    if (!inputValue.trim() || !apiUrl || !accessToken || loading) return

    let sessionId = currentSessionId
    if (!sessionId) {
      sessionId = await createSession()
      if (!sessionId) return
    }

    const userMessage = inputValue.trim()
    const tempId = Date.now()
    setInputValue('')
    setLoading(true)

    // Add temporary user message with unique temp ID
    setMessages(prev => [...prev, { id: tempId, role: 'user', content: userMessage, created_at: new Date().toISOString() }])

    try {
      const res = await fetch(`${apiUrl}/api/chat/sessions/${sessionId}/send/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: userMessage })
      })

      if (res.ok) {
        const data = await res.json()
        // Replace temp message with real messages from server
        setMessages(prev => {
          const withoutTemp = prev.filter(m => m.id !== tempId)
          return [...withoutTemp, data.user_message, data.ai_message]
        })
        fetchSessions()
      } else {
        const err = await res.json()
        setMessages(prev => [...prev, { id: tempId + 1, role: 'ai', content: `Error: ${err.detail || 'Failed to get response'}`, created_at: new Date().toISOString() }])
      }
    } catch (e) {
      setMessages(prev => [...prev, { id: tempId + 1, role: 'ai', content: 'Error: Failed to connect to server', created_at: new Date().toISOString() }])
    } finally {
      setLoading(false)
    }
  }

  function startNewChat() {
    setCurrentSessionId(null)
    setMessages([])
    setShowHistory(false)
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <aside className={`chat-panel ${open ? '' : 'chat-panel-collapsed'}`}>
      <div className="chat-head">
        <div className="chat-head-left">
          <span className="chat-head-icon">ðŸ’¬</span>
          <h3 className="chat-title">Health Assistant</h3>
        </div>
        <div className="chat-head-right">
          <button className="chat-icon-btn" aria-label="New chat" title="New chat" onClick={startNewChat}>
            +
          </button>
          <button className="chat-icon-btn" aria-label="History" title="History" onClick={() => setShowHistory(!showHistory)}>
            ðŸ•
          </button>
          <button className="chat-icon-btn" aria-label={open ? 'Close chat' : 'Open chat'} onClick={onToggle}>
            {open ? 'Ã—' : '+'}
          </button>
        </div>
      </div>

      {open ? (
        <>
          {showHistory ? (
            <div className="chat-body" style={{ padding: '1rem' }}>
              <h4 style={{ margin: '0 0 1rem', color: '#0f172a' }}>Chat History</h4>
              {sessions.length === 0 ? (
                <p style={{ color: '#71717a' }} className="animate-fadeIn">No previous chats</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {sessions.map((s, index) => (
                    <button
                      key={s.id}
                      onClick={() => loadSession(s.id)}
                      className="chat-history-item"
                      style={{
                        textAlign: 'left',
                        padding: '0.75rem',
                        border: '1px solid #e4e4e7',
                        borderRadius: '8px',
                        background: currentSessionId === s.id ? '#f4f4f5' : 'white',
                        cursor: 'pointer',
                        animationDelay: `${index * 0.05}s`
                      }}
                    >
                      <p style={{ margin: 0, fontWeight: 600, color: '#0f172a' }}>{s.title || `Chat ${s.id}`}</p>
                      <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem', color: '#71717a' }}>
                        {new Date(s.updated_at).toLocaleDateString()}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className={`chat-body ${messages.length === 0 ? 'chat-body-empty' : ''}`}>
              {messages.length === 0 ? (
                <div className="chat-welcome">
                  <div className="chat-welcome-icon">ðŸ’¬</div>
                  <h3 className="chat-welcome-title">Your Health Assistant</h3>
                  <p className="chat-welcome-subtitle">Ask about symptoms, medications, lifestyle tips, and get personalized health guidance</p>
                </div>
              ) : (
                <>
                  {messages.map((msg) => (
                    <div key={msg.id} className={`chat-message chat-message-${msg.role}`}>
                      <p className="chat-label">{msg.role === 'ai' ? 'AI' : 'You'}</p>
                      <p style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</p>
                    </div>
                  ))}
                  {loading && (
                    <div className="chat-message chat-message-ai">
                      <p className="chat-label">AI</p>
                      <div className="chat-thinking">
                        <div className="chat-thinking-dots">
                          <span className="chat-thinking-dot"></span>
                          <span className="chat-thinking-dot"></span>
                          <span className="chat-thinking-dot"></span>
                        </div>
                        <span className="chat-typing-text">Thinking...</span>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </>
              )}
            </div>
          )}

          <div className="chat-input">
            <div className="chat-input-wrapper">
              <input
                type="text"
                placeholder="Ask me anything about your health..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading || !accessToken}
              />
              <div className="chat-input-actions">
                <button className="chat-send-btn" aria-label="Send" onClick={sendMessage} disabled={loading || !inputValue.trim() || !accessToken}>
                  â†‘
                </button>
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="chat-collapsed">
          <p className="chat-collapsed-text">Chat is hidden</p>
          <button className="secondary-btn" onClick={onToggle}>Open chat</button>
        </div>
      )}
    </aside>
  )
}

function DocumentUploadModal({ 
  onClose, 
  onUpload, 
  uploading, 
  error,
  accessToken,
  apiUrl,
  onProfileUpdate
}: { 
  onClose: () => void
  onUpload: (files: FileList | null) => void
  uploading: boolean
  error: string | null
  accessToken: string | null
  apiUrl: string | undefined
  onProfileUpdate: (healthSummary: string) => void
}) {
  const [dragOver, setDragOver] = useState(false)
  const [uploadMode, setUploadMode] = useState<'documents' | 'ecg'>('documents')
  const [ecgFile, setEcgFile] = useState<File | null>(null)
  const [ecgPreview, setEcgPreview] = useState<string | null>(null)
  const [ecgAnalyzing, setEcgAnalyzing] = useState(false)
  const [ecgResult, setEcgResult] = useState<{label: string; message: string; confidence: number | null; status: string} | null>(null)
  const [ecgError, setEcgError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const ecgInputRef = useRef<HTMLInputElement>(null)

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    onUpload(e.dataTransfer.files)
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(true)
  }

  function handleDragLeave() {
    setDragOver(false)
  }

  function handleEcgSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) {
      if (!file.type.startsWith('image/')) {
        setEcgError('Please select an image file')
        return
      }
      setEcgFile(file)
      setEcgError(null)
      setEcgResult(null)
      const reader = new FileReader()
      reader.onloadend = () => setEcgPreview(reader.result as string)
      reader.readAsDataURL(file)
    }
  }

  async function handleEcgAnalyze() {
    if (!ecgFile || !accessToken || !apiUrl) return
    setEcgAnalyzing(true)
    setEcgError(null)
    try {
      const formData = new FormData()
      formData.append('ecg_image', ecgFile)
      const res = await fetch(`${apiUrl}/api/ecg/analyze/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
        body: formData,
      })
      const data = await res.json()
      if (data.success) {
        setEcgResult(data.prediction)
        if (data.profile?.health_summary) {
          onProfileUpdate(data.profile.health_summary)
        }
      } else {
        setEcgError(data.error || 'Analysis failed')
      }
    } catch {
      setEcgError('Failed to connect to server')
    } finally {
      setEcgAnalyzing(false)
    }
  }

  function resetEcg() {
    setEcgFile(null)
    setEcgPreview(null)
    setEcgResult(null)
    setEcgError(null)
    if (ecgInputRef.current) ecgInputRef.current.value = ''
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card doc-upload-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="section-title">Upload Medical Documents</h2>
          <button className="chat-icon-btn" onClick={onClose}>x</button>
        </div>
        
        <div className="upload-mode-tabs">
          <button className={`upload-mode-tab ${uploadMode === 'documents' ? 'active' : ''}`} onClick={() => setUploadMode('documents')}>Documents</button>
          <button className={`upload-mode-tab ${uploadMode === 'ecg' ? 'active' : ''}`} onClick={() => setUploadMode('ecg')}>ECG Diagnosis</button>
        </div>

        {uploadMode === 'documents' ? (
          <>
            <p className="section-subtitle">Upload prescriptions, lab reports, or medical records. AI will extract and analyze the information.</p>
            <div className={`upload-dropzone ${dragOver ? 'upload-dropzone-active' : ''}`} onDrop={handleDrop} onDragOver={handleDragOver} onDragLeave={handleDragLeave} onClick={() => fileInputRef.current?.click()}>
              <div className="upload-icon">📄</div>
              <p className="upload-text">Drag and drop files here or click to browse</p>
              <p className="upload-hint">Supports PDF, JPG, PNG (max 10MB)</p>
              <input ref={fileInputRef} type="file" multiple accept=".pdf,.jpg,.jpeg,.png" style={{ display: 'none' }} onChange={(e) => onUpload(e.target.files)} />
            </div>
            {error && <p className="error">{error}</p>}
            {uploading && <div className="upload-progress"><p>Processing documents with AI...</p></div>}
          </>
        ) : (
          <>
            <p className="section-subtitle">Upload a 12-lead ECG image for specialized cardiovascular disease detection using our trained ML model.</p>
            {!ecgPreview ? (
              <div className="upload-dropzone ecg-dropzone" onClick={() => ecgInputRef.current?.click()}>
                <div className="upload-icon ecg-heart">&#10084;</div>
                <p className="upload-text">Click to upload ECG image</p>
                <p className="upload-hint">JPEG or PNG, 12-lead ECG format</p>
                <input ref={ecgInputRef} type="file" accept="image/jpeg,image/png" style={{ display: 'none' }} onChange={handleEcgSelect} />
              </div>
            ) : (
              <div className="ecg-preview-area">
                <img src={ecgPreview} alt="ECG Preview" className="ecg-preview-img" />
                <button className="ecg-remove" onClick={resetEcg}>x</button>
              </div>
            )}
            {ecgError && <p className="error">{ecgError}</p>}
            {ecgResult && (
              <div className={`ecg-result-box status-${ecgResult.status}`}>
                <div className="ecg-result-header">
                  <span className={`ecg-status-badge ${ecgResult.status}`}>{ecgResult.status === 'normal' ? 'OK' : '!'}</span>
                  <div><strong>{ecgResult.label}</strong>{ecgResult.confidence && <span className="ecg-conf"> ({ecgResult.confidence.toFixed(0)}%)</span>}</div>
                </div>
                <p className="ecg-result-msg">{ecgResult.message}</p>
                {ecgResult.status !== 'normal' && <p className="ecg-disclaimer">This is an AI screening tool. Please consult a healthcare professional for diagnosis.</p>}
              </div>
            )}
            {ecgFile && !ecgResult && <button className="primary-btn ecg-analyze-btn" onClick={handleEcgAnalyze} disabled={ecgAnalyzing}>{ecgAnalyzing ? 'Analyzing...' : 'Analyze ECG'}</button>}
            {ecgResult && <button className="secondary-btn" onClick={resetEcg}>Analyze Another ECG</button>}
            <div className="ecg-info-box"><strong>Detects with high accuracy:</strong><ul><li><span className="dot green"></span> Normal ECG</li><li><span className="dot yellow"></span> Abnormal Heartbeat</li><li><span className="dot red"></span> Myocardial Infarction</li><li><span className="dot yellow"></span> History of MI</li></ul></div>
          </>
        )}
      </div>
    </div>
  )
}
export default App

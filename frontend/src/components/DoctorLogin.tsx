import { useState } from 'react'

type DoctorLoginProps = {
  onLogin: (token: string) => void
  apiUrl: string | undefined
}

export function DoctorLogin({ onLogin, apiUrl }: DoctorLoginProps) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!apiUrl || !password.trim()) return

    setLoading(true)
    setError(null)

    try {
      const res = await fetch(`${apiUrl}/api/doctor/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      })

      const data = await res.json()

      if (res.ok && data.success) {
        onLogin(data.token)
      } else {
        setError(data.detail || 'Invalid password')
      }
    } catch {
      setError('Connection failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="doctor-login-page">
      <div className="doctor-login-container">
        <div className="doctor-login-card">
          <div className="doctor-login-header">
            <div className="doctor-login-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </div>
            <h1>Doctor Portal</h1>
            <p>Access patient records and manage consultations</p>
          </div>

          <form onSubmit={handleSubmit} className="doctor-login-form">
            <div className="doctor-login-field">
              <label htmlFor="password">Access Code</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your access code"
                disabled={loading}
                autoFocus
              />
            </div>

            {error && <div className="doctor-login-error">{error}</div>}

            <button type="submit" disabled={loading || !password.trim()} className="doctor-login-btn">
              {loading ? (
                <span className="doctor-login-spinner" />
              ) : (
                <>
                  <span>Sign In</span>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                </>
              )}
            </button>
          </form>

          <div className="doctor-login-footer">
            <p>Protected health information - Authorized access only</p>
          </div>
        </div>

        <div className="doctor-login-features">
          <div className="feature-item">
            <div className="feature-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 12h6M12 9v6M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z" />
              </svg>
            </div>
            <div className="feature-text">
              <h3>Complete Patient Profiles</h3>
              <p>Access comprehensive patient information at a glance</p>
            </div>
          </div>
          <div className="feature-item">
            <div className="feature-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
              </svg>
            </div>
            <div className="feature-text">
              <h3>AI-Powered Summaries</h3>
              <p>Get intelligent case summaries generated instantly</p>
            </div>
          </div>
          <div className="feature-item">
            <div className="feature-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
            </div>
            <div className="feature-text">
              <h3>Real-time Health Data</h3>
              <p>Monitor vitals and symptom timelines effectively</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

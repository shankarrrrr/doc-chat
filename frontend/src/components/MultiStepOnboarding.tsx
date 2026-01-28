import { useState, useRef, useEffect } from 'react'
import type { FormEvent } from 'react'

export type HealthOnboardingPayload = {
  full_name: string
  age?: number
  sex?: string
  height?: number
  weight?: number
  blood_type?: string
  allergies?: string
  conditions?: string
  medications?: string
  medical_history?: string
  past_reports?: string
  prescriptions?: string
  symptoms_current?: string
  symptoms_past?: string
  location?: string
  smoking_status?: string
  alcohol_consumption?: string
  exercise_frequency?: string
  diet_type?: string
  sleep_hours?: number
  stress_level?: string
  family_history?: string
  health_goals?: string
  emergency_contact_name?: string
  emergency_contact_phone?: string
  blood_pressure?: string
  heart_rate?: number
  temperature_c?: number
  spo2?: number
  // AI-extracted fields from documents
  diagnosis?: string
  treatment_plan?: string
  doctor_notes?: string
}

type StepProps = {
  data: HealthOnboardingPayload
  updateData: (updates: Partial<HealthOnboardingPayload>) => void
  disabled?: boolean
  accessToken?: string | null
  apiUrl?: string
  onVoiceStateChange?: (hasVoiceInput: boolean, generateSummary: () => Promise<void>) => void
}

const text = (value: string) => value

const numberOrUndefined = (value: string) => {
  const cleaned = value.trim()
  if (!cleaned) return undefined
  const num = Number(cleaned)
  return Number.isFinite(num) ? num : undefined
}

function StepIntro({ data, updateData, disabled, initialFullName }: StepProps & { initialFullName?: string }) {
  return (
    <div className="field-grid">
      <div>
        <p className="pill">Step 1 · Essentials</p>
        <h2 className="section-title">About you</h2>
        <p className="section-subtitle">Core demographics to personalize care.</p>
      </div>

      <div className="field">
        <label htmlFor="full_name">Full name *</label>
        <input
          id="full_name"
          value={data.full_name}
          onChange={(e) => updateData({ full_name: text(e.target.value) })}
          disabled={disabled}
          autoComplete="name"
          placeholder={initialFullName ? `e.g., ${initialFullName}` : 'Enter your full name'}
        />
      </div>

      <div className="field-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
        <div className="field">
          <label htmlFor="age">Age</label>
          <input
            id="age"
            value={data.age ?? ''}
            onChange={(e) => updateData({ age: numberOrUndefined(e.target.value) })}
            disabled={disabled}
            type="number"
            min={0}
            max={130}
            inputMode="numeric"
          />
        </div>

        <div className="field">
          <label htmlFor="sex">Sex</label>
          <select
            id="sex"
            value={data.sex ?? ''}
            onChange={(e) => updateData({ sex: e.target.value || undefined })}
            disabled={disabled}
          >
            <option value="">Select</option>
            <option value="female">Female</option>
            <option value="male">Male</option>
            <option value="other">Other</option>
            <option value="prefer_not_to_say">Prefer not to say</option>
          </select>
        </div>
      </div>

      <div className="field-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
        <div className="field">
          <label>Height (cm)</label>
          <input
            value={data.height ?? ''}
            onChange={(e) => updateData({ height: numberOrUndefined(e.target.value) })}
            disabled={disabled}
            type="number"
            min={0}
            inputMode="numeric"
          />
        </div>
        <div className="field">
          <label>Weight (kg)</label>
          <input
            value={data.weight ?? ''}
            onChange={(e) => updateData({ weight: numberOrUndefined(e.target.value) })}
            disabled={disabled}
            type="number"
            min={0}
            inputMode="numeric"
          />
        </div>
        <div className="field">
          <label>Blood type</label>
          <select
            value={data.blood_type ?? ''}
            onChange={(e) => updateData({ blood_type: e.target.value || undefined })}
            disabled={disabled}
          >
            <option value="">Select</option>
            <option value="A+">A+</option>
            <option value="A-">A-</option>
            <option value="B+">B+</option>
            <option value="B-">B-</option>
            <option value="AB+">AB+</option>
            <option value="AB-">AB-</option>
            <option value="O+">O+</option>
            <option value="O-">O-</option>
            <option value="unknown">Don't know</option>
          </select>
        </div>
      </div>
    </div>
  )
}

function StepMedical({ data, updateData, disabled }: StepProps) {
  return (
    <div className="field-grid">
      <div>
        <p className="pill">Step 2 · Medical history</p>
        <h2 className="section-title">Long-term record</h2>
        <p className="section-subtitle">Past conditions, reports, and prescriptions.</p>
      </div>

      <div className="field">
        <label htmlFor="medical_history">Medical history</label>
        <textarea
          id="medical_history"
          value={data.medical_history ?? ''}
          onChange={(e) => updateData({ medical_history: e.target.value || undefined })}
          disabled={disabled}
          placeholder="Key diagnoses, surgeries, hospitalizations"
        />
      </div>

      <div className="field">
        <label htmlFor="past_reports">Past reports & prescriptions</label>
        <textarea
          id="past_reports"
          value={data.past_reports ?? ''}
          onChange={(e) => updateData({ past_reports: e.target.value || undefined })}
          disabled={disabled}
          placeholder="Summaries of labs, imaging, prescriptions"
        />
      </div>

      <div className="field-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        <div className="field">
          <label htmlFor="prescriptions">Current prescriptions</label>
          <textarea
            id="prescriptions"
            value={data.prescriptions ?? ''}
            onChange={(e) => updateData({ prescriptions: e.target.value || undefined })}
            disabled={disabled}
            placeholder="e.g., metformin 500mg BID"
          />
        </div>
        <div className="field">
          <label htmlFor="medications">Medications</label>
          <textarea
            id="medications"
            value={data.medications ?? ''}
            onChange={(e) => updateData({ medications: e.target.value || undefined })}
            disabled={disabled}
            placeholder="Supplements or other meds"
          />
        </div>
      </div>

      <div className="field-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        <div className="field">
          <label htmlFor="allergies">Allergies</label>
          <textarea
            id="allergies"
            value={data.allergies ?? ''}
            onChange={(e) => updateData({ allergies: e.target.value || undefined })}
            disabled={disabled}
            placeholder="e.g., penicillin, peanuts"
          />
        </div>
        <div className="field">
          <label htmlFor="conditions">Chronic conditions</label>
          <textarea
            id="conditions"
            value={data.conditions ?? ''}
            onChange={(e) => updateData({ conditions: e.target.value || undefined })}
            disabled={disabled}
            placeholder="e.g., diabetes, hypertension"
          />
        </div>
      </div>
    </div>
  )
}

function StepSymptoms({ data, updateData, disabled, accessToken, apiUrl, onVoiceStateChange }: StepProps) {
  const [locating, setLocating] = useState(false)
  const [locationError, setLocationError] = useState<string | null>(null)
  const [useVoice, setUseVoice] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [voiceError, setVoiceError] = useState<string | null>(null)
  const [voiceMessages, setVoiceMessages] = useState<Array<{role: 'user'|'assistant', content: string}>>([])
  const [voiceSummary, setVoiceSummary] = useState<{
    chief_complaint: string
    symptoms: Array<{symptom: string, duration?: string, severity?: string}>
    summary_for_patient: string
    recommended_urgency: string
    suggested_specialty?: string
  } | null>(null)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const isPlayingRef = useRef(false)
  const isProcessingRef = useRef(false)

  // Text-to-Speech using Sarvam (Indian) or Gemini TTS
  const speakText = async (text: string, language: string = 'en') => {
    // Prevent double playback using ref
    if (isPlayingRef.current) {
      console.log('Already playing, skipping...')
      return
    }
    isPlayingRef.current = true
    
    // Stop any currently playing audio first
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
    
    if (!accessToken || !apiUrl) {
      isPlayingRef.current = false
      speakWithWebSpeech(text)
      return
    }

    setIsSpeaking(true)
    try {
      console.log(`Calling TTS (lang: ${language})...`)
      const res = await fetch(`${apiUrl}/api/voice/tts/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
        body: JSON.stringify({ text, language }),
      })
      const data = await res.json()
      console.log('TTS response:', data.success, data.mime_type)
      
      if (data.success && data.audio) {
        const audioBlob = Uint8Array.from(atob(data.audio), c => c.charCodeAt(0))
        const blob = new Blob([audioBlob], { type: data.mime_type })
        const audioUrl = URL.createObjectURL(blob)
        const audio = new Audio(audioUrl)
        audioRef.current = audio
        
        audio.onended = () => {
          console.log('TTS ended')
          setIsSpeaking(false)
          URL.revokeObjectURL(audioUrl)
          audioRef.current = null
          isPlayingRef.current = false
        }
        audio.onerror = (e) => {
          console.error('Audio playback error:', e)
          setIsSpeaking(false)
          URL.revokeObjectURL(audioUrl)
          audioRef.current = null
          isPlayingRef.current = false
        }
        
        await audio.play()
        console.log('TTS playing')
        return // Don't fall through to Web Speech
      }
      
      // Only use Web Speech if backend TTS failed
      console.log('TTS failed, using Web Speech fallback')
      setIsSpeaking(false)
      isPlayingRef.current = false
      speakWithWebSpeech(text)
    } catch (err) {
      console.error('TTS error:', err)
      setIsSpeaking(false)
      isPlayingRef.current = false
      speakWithWebSpeech(text)
    }
  }

  const speakWithWebSpeech = (text: string) => {
    // Web Speech is only fallback - don't use if already playing
    if (isPlayingRef.current) {
      console.log('Already playing, skipping Web Speech')
      return
    }
    
    console.log('speakWithWebSpeech called with:', text.substring(0, 50) + '...')
    
    if (!('speechSynthesis' in window)) {
      console.error('Speech synthesis not supported')
      setIsSpeaking(false)
      isPlayingRef.current = false
      return
    }
    
    window.speechSynthesis.cancel()
    
    const speak = () => {
      // Double check we're not already playing
      if (isPlayingRef.current && isSpeaking) {
        return
      }
      isPlayingRef.current = true
      
      console.log('Speaking now...')
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.rate = 0.9
      utterance.pitch = 1
      utterance.volume = 1
      
      // Try to find appropriate voice
      const voices = window.speechSynthesis.getVoices()
      console.log('Available voices:', voices.length)
      
      const hasHindi = /[\u0900-\u097F]/.test(text)
      if (hasHindi) {
        const hindiVoice = voices.find(v => v.lang.startsWith('hi'))
        if (hindiVoice) {
          console.log('Using Hindi voice:', hindiVoice.name)
          utterance.voice = hindiVoice
        }
      }
      
      utterance.onstart = () => {
        console.log('Speech started')
        setIsSpeaking(true)
      }
      utterance.onend = () => {
        console.log('Speech ended')
        setIsSpeaking(false)
        isPlayingRef.current = false
      }
      utterance.onerror = (e) => {
        console.error('Speech error:', e.error)
        setIsSpeaking(false)
        isPlayingRef.current = false
      }
      
      window.speechSynthesis.speak(utterance)
    }
    
    // Voices might not be loaded yet
    const voices = window.speechSynthesis.getVoices()
    if (voices.length === 0) {
      console.log('Waiting for voices to load...')
      window.speechSynthesis.onvoiceschanged = () => {
        console.log('Voices loaded')
        speak()
      }
    } else {
      speak()
    }
  }

  const startVoiceRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []
      
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      
      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        stream.getTracks().forEach(track => track.stop())
        await processVoiceAudio(blob)
      }
      
      mediaRecorder.start()
      setIsRecording(true)
      setVoiceError(null)
    } catch {
      setVoiceError('Could not access microphone')
    }
  }

  const stopVoiceRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const processVoiceAudio = async (blob: Blob) => {
    if (!accessToken || !apiUrl) return
    
    // Prevent double processing using ref (state updates are async)
    if (isProcessingRef.current) {
      console.log('Already processing, skipping duplicate call')
      return
    }
    isProcessingRef.current = true
    setIsProcessing(true)
    
    // Reset the playing ref at start of new processing
    isPlayingRef.current = false
    
    try {
      const reader = new FileReader()
      const base64 = await new Promise<string>((resolve) => {
        reader.onloadend = () => resolve((reader.result as string).split(',')[1])
        reader.readAsDataURL(blob)
      })

      // Transcribe
      const transcribeRes = await fetch(`${apiUrl}/api/voice/transcribe/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
        body: JSON.stringify({ audio: base64, mime_type: 'audio/webm' }),
      })
      const transcribeData = await transcribeRes.json()
      if (!transcribeData.success) throw new Error(transcribeData.error)

      const userMsg = transcribeData.transcription
      const detectedLang = transcribeData.language || 'en'
      const newMessages = [...voiceMessages, { role: 'user' as const, content: userMsg }]
      setVoiceMessages(newMessages)

      // Get AI response - pass detected language
      const convRes = await fetch(`${apiUrl}/api/voice/conversation/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
        body: JSON.stringify({ message: userMsg, history: newMessages, language: detectedLang }),
      })
      const convData = await convRes.json()
      if (!convData.success) throw new Error(convData.error)

      const updatedMessages = [...newMessages, { role: 'assistant' as const, content: convData.response }]
      setVoiceMessages(updatedMessages)

      // Speak the AI response - use detected language for TTS
      speakText(convData.response, detectedLang)

      if (convData.is_complete) {
        await generateVoiceSummary(updatedMessages)
      }
    } catch (err) {
      setVoiceError(err instanceof Error ? err.message : 'Voice processing failed')
    } finally {
      setIsProcessing(false)
      isProcessingRef.current = false
    }
  }

  const generateVoiceSummary = async (messages: Array<{role: string, content: string}>) => {
    if (!accessToken || !apiUrl) return
    try {
      const res = await fetch(`${apiUrl}/api/voice/summary/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
        body: JSON.stringify({ history: messages }),
      })
      const data = await res.json()
      if (data.success) {
        setVoiceSummary(data.summary)
        updateData({ symptoms_current: data.summary.chief_complaint })
      }
    } catch (err) {
      setVoiceError('Failed to generate summary')
    }
  }

  // Expose function to generate summary (called by parent on form submit)
  const getVoiceData = () => ({ messages: voiceMessages, hasSummary: !!voiceSummary })
  
  // Store in ref so parent can access
  useRef<{ getVoiceData: typeof getVoiceData, generateSummary: () => Promise<void> } | null>(null)
  
  const generateSummaryIfNeeded = async () => {
    if (voiceMessages.length > 0 && !voiceSummary) {
      await generateVoiceSummary(voiceMessages)
    }
  }

  // Notify parent about voice state changes
  useEffect(() => {
    if (onVoiceStateChange && useVoice) {
      onVoiceStateChange(voiceMessages.length > 0, generateSummaryIfNeeded)
    }
  }, [useVoice, voiceMessages.length, voiceSummary])

  const reverseGeocode = async (lat: number, lon: number) => {
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lon}&zoom=10&addressdetails=1`,
        { headers: { 'Accept-Language': 'en' } },
      )
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const body = (await res.json()) as { address?: Record<string, string>; display_name?: string }
      const addr = body.address || {}
      const city = addr.city || addr.town || addr.village || addr.hamlet || addr.county
      const state = addr.state || addr.region
      const country = addr.country
      const parts = [city, state, country].filter(Boolean)
      return parts.join(', ') || body.display_name || `${lat.toFixed(4)}, ${lon.toFixed(4)}`
    } catch (err) {
      console.warn('Reverse geocode failed', err)
      return `${lat.toFixed(4)}, ${lon.toFixed(4)}`
    }
  }

  const useCurrentLocation = () => {
    if (!navigator?.geolocation) {
      setLocationError('Geolocation is not available on this device/browser')
      return
    }

    setLocating(true)
    setLocationError(null)

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords
        const fallback = `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`
        updateData({ location: fallback })
        const friendly = await reverseGeocode(latitude, longitude)
        updateData({ location: friendly })
        setLocating(false)
      },
      (err) => {
        let errorMessage = 'Unable to fetch location'
        if (err.code === 1) {
          errorMessage = 'Location permission denied. Please allow location access.'
        } else if (err.code === 2) {
          errorMessage = 'Location unavailable. Please enter manually.'
        } else if (err.code === 3) {
          errorMessage = 'Location request timed out. Please try again or enter manually.'
        }
        setLocationError(errorMessage)
        setLocating(false)
      },
      { enableHighAccuracy: false, timeout: 30000, maximumAge: 300000 },
    )
  }

  return (
    <div className="field-grid">
      <div>
        <p className="pill">Step 3 · Symptoms & location</p>
        <h2 className="section-title">Current concerns</h2>
        <p className="section-subtitle">Helps AI triage and recommend care nearby.</p>
      </div>

      {/* Voice/Text Toggle */}
      <div className="input-mode-toggle">
        <button
          type="button"
          className={`toggle-btn ${!useVoice ? 'active' : ''}`}
          onClick={() => setUseVoice(false)}
        >
          Type symptoms
        </button>
        <button
          type="button"
          className={`toggle-btn ${useVoice ? 'active' : ''}`}
          onClick={() => setUseVoice(true)}
          disabled={!accessToken || !apiUrl}
        >
          Speak symptoms
        </button>
      </div>

      {useVoice ? (
        <div className="voice-input-section">
          {!voiceSummary ? (
            <>
              <p className="voice-hint">Speak in any language - Hindi, Tamil, Telugu, Bengali, Marathi, or English</p>
              
              <div className="voice-messages-mini">
                {voiceMessages.length === 0 && (
                  <div className="voice-msg assistant">
                    Hello! Please tell me what symptoms you're experiencing. I'll ask a few follow-up questions.
                  </div>
                )}
                {voiceMessages.map((msg, i) => (
                  <div key={i} className={`voice-msg ${msg.role}`}>
                    {msg.content}
                  </div>
                ))}
                {isProcessing && (
                  <div className="voice-msg assistant processing">Thinking...</div>
                )}
              </div>

              {voiceError && <p className="error">{voiceError}</p>}

              <div className="voice-controls-mini">
                <button
                  type="button"
                  className={`voice-btn ${isRecording ? 'recording' : ''} ${isSpeaking ? 'speaking' : ''}`}
                  onMouseDown={startVoiceRecording}
                  onMouseUp={stopVoiceRecording}
                  onMouseLeave={stopVoiceRecording}
                  onTouchStart={startVoiceRecording}
                  onTouchEnd={stopVoiceRecording}
                  disabled={isProcessing || disabled || isSpeaking}
                >
                  {isRecording ? 'Release to send' : isProcessing ? 'Processing...' : isSpeaking ? 'Listening...' : 'Hold to speak'}
                </button>
              </div>
              {voiceMessages.length > 0 && (
                <p className="voice-continue-hint">Continue the conversation or click Next to generate summary</p>
              )}
            </>
          ) : (
            <div className="voice-summary-mini">
              <div className={`urgency-badge-mini ${voiceSummary.recommended_urgency}`}>
                {voiceSummary.recommended_urgency === 'emergency' ? 'Emergency' :
                 voiceSummary.recommended_urgency === 'urgent' ? 'Urgent' :
                 voiceSummary.recommended_urgency === 'soon' ? 'Schedule Soon' : 'Routine'}
              </div>
              <h4>Summary</h4>
              <p>{voiceSummary.summary_for_patient}</p>
              {voiceSummary.suggested_specialty && (
                <p className="specialty-hint">Suggested: {voiceSummary.suggested_specialty}</p>
              )}
              <button type="button" className="secondary-btn" onClick={() => { setVoiceSummary(null); setVoiceMessages([]) }}>
                Start Over
              </button>
            </div>
          )}
        </div>
      ) : (
        <>
          <div className="field">
            <label htmlFor="symptoms_current">Current symptoms *</label>
            <textarea
              id="symptoms_current"
              value={data.symptoms_current ?? ''}
              onChange={(e) => updateData({ symptoms_current: e.target.value || undefined })}
              disabled={disabled}
              placeholder="e.g., chest discomfort, shortness of breath"
            />
          </div>

          <div className="field">
            <label htmlFor="symptoms_past">Past symptoms</label>
            <textarea
              id="symptoms_past"
              value={data.symptoms_past ?? ''}
              onChange={(e) => updateData({ symptoms_past: e.target.value || undefined })}
              disabled={disabled}
              placeholder="e.g., prior episodes, resolved issues"
            />
          </div>
        </>
      )}

      <div className="field">
        <label htmlFor="location">Location (city / area)</label>
        <div className="location-row">
          <input
            id="location"
            value={data.location ?? ''}
            onChange={(e) => updateData({ location: e.target.value || undefined })}
            disabled={disabled}
            placeholder="e.g., Mumbai, Andheri (optional)"
          />
          <button
            type="button"
            className="secondary-btn"
            onClick={useCurrentLocation}
            disabled={disabled || locating}
          >
            {locating ? 'Detecting…' : 'Use GPS'}
          </button>
        </div>
        <p className="location-helper">We’ll use your device GPS to suggest nearby care options.</p>
        {locationError ? <p className="error" style={{ marginTop: '0.5rem' }}>{locationError}</p> : null}
      </div>
    </div>
  )
}

// Kept for future use - not currently in onboarding flow
export function StepLifestyle({ data, updateData, disabled }: StepProps) {
  return (
    <div className="field-grid">
      <div>
        <p className="pill">Step 4 · Lifestyle & vitals</p>
        <h2 className="section-title">Habits, vitals, and safety</h2>
        <p className="section-subtitle">Daily routines, vitals, and emergency contacts.</p>
      </div>

      <div className="field-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))' }}>
        <div className="field">
          <label htmlFor="exercise">Exercise</label>
          <select
            id="exercise"
            value={data.exercise_frequency ?? ''}
            onChange={(e) => updateData({ exercise_frequency: e.target.value || undefined })}
            disabled={disabled}
          >
            <option value="">Select</option>
            <option value="sedentary">Sedentary</option>
            <option value="light">1-2 days/week</option>
            <option value="moderate">3-4 days/week</option>
            <option value="active">5-6 days/week</option>
            <option value="very_active">Daily</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="diet">Diet</label>
          <select
            id="diet"
            value={data.diet_type ?? ''}
            onChange={(e) => updateData({ diet_type: e.target.value || undefined })}
            disabled={disabled}
          >
            <option value="">Select</option>
            <option value="omnivore">Omnivore</option>
            <option value="vegetarian">Vegetarian</option>
            <option value="vegan">Vegan</option>
            <option value="pescatarian">Pescatarian</option>
            <option value="keto">Keto</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="smoking">Smoking</label>
          <select
            id="smoking"
            value={data.smoking_status ?? ''}
            onChange={(e) => updateData({ smoking_status: e.target.value || undefined })}
            disabled={disabled}
          >
            <option value="">Select</option>
            <option value="never">Never</option>
            <option value="former">Former</option>
            <option value="occasional">Occasional</option>
            <option value="regular">Regular</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="alcohol">Alcohol</label>
          <select
            id="alcohol"
            value={data.alcohol_consumption ?? ''}
            onChange={(e) => updateData({ alcohol_consumption: e.target.value || undefined })}
            disabled={disabled}
          >
            <option value="">Select</option>
            <option value="none">None</option>
            <option value="occasional">Occasional</option>
            <option value="moderate">Moderate</option>
            <option value="heavy">Heavy</option>
          </select>
        </div>
      </div>

      <div className="field-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))' }}>
        <div className="field">
          <label>Sleep (hrs)</label>
          <input
            value={data.sleep_hours ?? ''}
            onChange={(e) => updateData({ sleep_hours: numberOrUndefined(e.target.value) })}
            disabled={disabled}
            type="number"
            min={0}
            max={24}
            inputMode="decimal"
          />
        </div>
        <div className="field">
          <label>Stress</label>
          <select
            value={data.stress_level ?? ''}
            onChange={(e) => updateData({ stress_level: e.target.value || undefined })}
            disabled={disabled}
          >
            <option value="">Select</option>
            <option value="low">Low</option>
            <option value="moderate">Moderate</option>
            <option value="high">High</option>
            <option value="very_high">Very high</option>
          </select>
        </div>
      </div>

      <div className="field-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))' }}>
        <div className="field">
          <label htmlFor="blood_pressure">Blood pressure</label>
          <input
            id="blood_pressure"
            value={data.blood_pressure ?? ''}
            onChange={(e) => updateData({ blood_pressure: e.target.value || undefined })}
            disabled={disabled}
            placeholder="e.g., 120/80"
          />
        </div>
        <div className="field">
          <label htmlFor="heart_rate">Heart rate (bpm)</label>
          <input
            id="heart_rate"
            value={data.heart_rate ?? ''}
            onChange={(e) => updateData({ heart_rate: numberOrUndefined(e.target.value) })}
            disabled={disabled}
            type="number"
            min={0}
            inputMode="numeric"
          />
        </div>
        <div className="field">
          <label htmlFor="temperature_c">Temperature (°C)</label>
          <input
            id="temperature_c"
            value={data.temperature_c ?? ''}
            onChange={(e) => updateData({ temperature_c: numberOrUndefined(e.target.value) })}
            disabled={disabled}
            type="number"
            step="0.1"
            min={0}
            inputMode="decimal"
          />
        </div>
        <div className="field">
          <label htmlFor="spo2">SpO₂ (%)</label>
          <input
            id="spo2"
            value={data.spo2 ?? ''}
            onChange={(e) => updateData({ spo2: numberOrUndefined(e.target.value) })}
            disabled={disabled}
            type="number"
            min={0}
            max={100}
            inputMode="numeric"
          />
        </div>
      </div>

      <div className="field">
        <label>Family history</label>
        <textarea
          value={data.family_history ?? ''}
          onChange={(e) => updateData({ family_history: e.target.value || undefined })}
          disabled={disabled}
          placeholder="e.g., heart disease, cancer"
        />
      </div>

      <div className="field">
        <label>Health goals</label>
        <textarea
          value={data.health_goals ?? ''}
          onChange={(e) => updateData({ health_goals: e.target.value || undefined })}
          disabled={disabled}
          placeholder="e.g., improve sleep, manage stress"
        />
      </div>

      <div className="field-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))' }}>
        <div className="field">
          <label>Emergency contact name</label>
          <input
            value={data.emergency_contact_name ?? ''}
            onChange={(e) => updateData({ emergency_contact_name: e.target.value || undefined })}
            disabled={disabled}
          />
        </div>
        <div className="field">
          <label>Emergency phone</label>
          <input
            value={data.emergency_contact_phone ?? ''}
            onChange={(e) => updateData({ emergency_contact_phone: e.target.value || undefined })}
            disabled={disabled}
            type="tel"
            inputMode="tel"
          />
        </div>
      </div>
    </div>
  )
}

const STEPS = [
  { title: 'Essentials', component: StepIntro },
  { title: 'Medical history', component: StepMedical },
  { title: 'Symptoms & location', component: StepSymptoms },
]

type MultiStepOnboardingProps = {
  initialFullName: string
  onSubmit: (payload: HealthOnboardingPayload) => Promise<void>
  disabled?: boolean
  accessToken?: string | null
  apiUrl?: string
}

export function HealthQuestionnaire({ initialFullName, onSubmit, disabled, accessToken, apiUrl }: MultiStepOnboardingProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [data, setData] = useState<HealthOnboardingPayload>({
    full_name: '', // Don't pre-fill - make user consciously enter their name
  })
  const [error, setError] = useState<string | null>(null)
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false)
  const voiceGenerateSummaryRef = useRef<(() => Promise<void>) | null>(null)
  const hasVoiceInputRef = useRef(false)

  const isLastStep = currentStep === STEPS.length - 1

  const updateData = (updates: Partial<HealthOnboardingPayload>) => {
    setData((prev) => ({ ...prev, ...updates }))
  }

  const handleVoiceStateChange = (hasInput: boolean, generateSummary: () => Promise<void>) => {
    hasVoiceInputRef.current = hasInput
    voiceGenerateSummaryRef.current = generateSummary
  }

  const validateStep = (stepIndex: number): string | null => {
    if (stepIndex === 0 && !data.full_name.trim()) return 'Full name is required'
    if (stepIndex === 2) {
      if (!data.symptoms_current?.trim()) return 'Please describe your current symptoms'
      // Location is optional now
    }
    return null
  }

  const handleNext = () => {
    const validationError = validateStep(currentStep)
    if (validationError) {
      setError(validationError)
      return
    }
    setError(null)
    setCurrentStep((prev) => Math.min(prev + 1, STEPS.length - 1))
  }

  const handleBack = () => {
    setError(null)
    setCurrentStep((prev) => Math.max(prev - 1, 0))
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    
    // Only submit on the last step when clicking Finish
    if (!isLastStep) {
      return
    }
    
    // Auto-generate voice summary if user has voice input but no summary yet
    if (hasVoiceInputRef.current && voiceGenerateSummaryRef.current && !data.symptoms_current?.trim()) {
      setIsGeneratingSummary(true)
      try {
        await voiceGenerateSummaryRef.current()
        // Wait a bit for state to update
        await new Promise(resolve => setTimeout(resolve, 500))
      } finally {
        setIsGeneratingSummary(false)
      }
    }
    
    const validationError = validateStep(currentStep)
    if (validationError) {
      setError(validationError)
      return
    }
    
    // Final submission - validate required across flow
    const normalizedName = data.full_name.trim()
    if (!normalizedName) {
      setError('Full name is required')
      return
    }
    if (!data.symptoms_current?.trim()) {
      setError('Please describe your current symptoms')
      return
    }
    // Location is optional
    setError(null)
    const payload: HealthOnboardingPayload = {
      ...data,
      full_name: normalizedName,
      symptoms_current: data.symptoms_current.trim(),
      location: data.location?.trim() || undefined,
    }

    try {
      await onSubmit(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  const StepComponent = STEPS[currentStep].component

  return (
    <div className="questionnaire-card">
      {/* Progress Steps */}
      <div className="questionnaire-progress">
        {STEPS.map((step, index) => (
          <div 
            key={index} 
            className={`questionnaire-step ${index === currentStep ? 'active' : ''} ${index < currentStep ? 'completed' : ''}`}
          >
            <div className="questionnaire-step-indicator">
              {index < currentStep ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              ) : (
                <span>{index + 1}</span>
              )}
            </div>
            <span className="questionnaire-step-title">{step.title}</span>
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="questionnaire-form" onKeyDown={(e) => {
        // Prevent Enter key from submitting the form except when focused on submit button
        if (e.key === 'Enter' && e.target instanceof HTMLElement && e.target.tagName !== 'BUTTON') {
          e.preventDefault()
        }
      }}>
        <div className="questionnaire-content">
          {currentStep === 0 ? (
            <StepIntro data={data} updateData={updateData} disabled={disabled} initialFullName={initialFullName} />
          ) : (
            <StepComponent 
              data={data} 
              updateData={updateData} 
              disabled={disabled || isGeneratingSummary} 
              accessToken={accessToken} 
              apiUrl={apiUrl}
              onVoiceStateChange={handleVoiceStateChange}
            />
          )}
        </div>

        {error && <p className="error questionnaire-error">{error}</p>}

        <div className="questionnaire-actions">
          <button
            type="button"
            onClick={handleBack}
            disabled={currentStep === 0 || disabled}
            className="questionnaire-btn questionnaire-btn-back"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
            Back
          </button>

          {isLastStep ? (
            <button type="submit" disabled={disabled || isGeneratingSummary} className="questionnaire-btn questionnaire-btn-primary">
              {isGeneratingSummary ? 'Generating Summary…' : disabled ? 'Saving…' : 'Complete Setup'}
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </button>
          ) : (
            <button type="button" onClick={handleNext} disabled={disabled} className="questionnaire-btn questionnaire-btn-primary">
              Continue
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
            </button>
          )}
        </div>
      </form>
    </div>
  )
}

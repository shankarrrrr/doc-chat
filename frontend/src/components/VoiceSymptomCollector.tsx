import { useState, useRef, useEffect } from 'react'

type Message = {
  role: 'user' | 'assistant'
  content: string
}

type SymptomSummary = {
  chief_complaint: string
  symptoms: Array<{
    symptom: string
    duration: string
    severity: string
    location?: string
  }>
  summary_for_patient: string
  summary_for_doctor: string
  recommended_urgency: string
  suggested_specialty: string
  language_detected: string
}

type VoiceSymptomCollectorProps = {
  accessToken: string | null
  apiUrl: string | undefined
  onComplete: (summary: SymptomSummary, symptoms: string) => void
  onCancel: () => void
}

export function VoiceSymptomCollector({ accessToken, apiUrl, onComplete, onCancel }: VoiceSymptomCollectorProps) {
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [currentTranscript, setCurrentTranscript] = useState('')
  const [, setLanguage] = useState('en')
  const [languageName, setLanguageName] = useState('English')
  const [error, setError] = useState<string | null>(null)
  const [summary, setSummary] = useState<SymptomSummary | null>(null)
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false)
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    // Start with a greeting
    setMessages([{
      role: 'assistant',
      content: 'Hello! I\'m here to help collect information about your symptoms. Please tell me what\'s been bothering you. You can speak in any language you\'re comfortable with - Hindi, Tamil, Telugu, Bengali, or any other language.'
    }])
  }, [])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []
      
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data)
        }
      }
      
      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        stream.getTracks().forEach(track => track.stop())
        await processAudio(blob)
      }
      
      mediaRecorder.start()
      setIsRecording(true)
      setError(null)
    } catch (err) {
      setError('Could not access microphone. Please allow microphone access.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const processAudio = async (blob: Blob) => {
    if (!accessToken || !apiUrl) return
    
    setIsProcessing(true)
    
    try {
      // Convert blob to base64
      const reader = new FileReader()
      const base64Promise = new Promise<string>((resolve) => {
        reader.onloadend = () => {
          const base64 = (reader.result as string).split(',')[1]
          resolve(base64)
        }
      })
      reader.readAsDataURL(blob)
      const audioBase64 = await base64Promise
      
      // Transcribe audio
      const transcribeRes = await fetch(`${apiUrl}/api/voice/transcribe/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          audio: audioBase64,
          mime_type: 'audio/webm'
        }),
      })
      
      const transcribeData = await transcribeRes.json()
      
      if (!transcribeData.success) {
        throw new Error(transcribeData.error || 'Transcription failed')
      }
      
      const userMessage = transcribeData.transcription
      setCurrentTranscript(userMessage)
      setLanguage(transcribeData.language)
      setLanguageName(transcribeData.language_name)
      
      // Add user message
      const newMessages: Message[] = [...messages, { role: 'user', content: userMessage }]
      setMessages(newMessages)
      
      // Get AI response
      const convRes = await fetch(`${apiUrl}/api/voice/conversation/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          message: userMessage,
          history: newMessages,
          language: transcribeData.language
        }),
      })
      
      const convData = await convRes.json()
      
      if (!convData.success) {
        throw new Error(convData.error || 'Conversation failed')
      }
      
      setMessages([...newMessages, { role: 'assistant', content: convData.response }])
      
      // Check if conversation is complete
      if (convData.is_complete) {
        await generateSummary([...newMessages, { role: 'assistant', content: convData.response }])
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process audio')
    } finally {
      setIsProcessing(false)
      setCurrentTranscript('')
    }
  }

  const generateSummary = async (conversationHistory: Message[]) => {
    if (!accessToken || !apiUrl) return
    
    setIsGeneratingSummary(true)
    
    try {
      const res = await fetch(`${apiUrl}/api/voice/summary/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          history: conversationHistory
        }),
      })
      
      const data = await res.json()
      
      if (data.success) {
        setSummary(data.summary)
      } else {
        throw new Error(data.error || 'Failed to generate summary')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate summary')
    } finally {
      setIsGeneratingSummary(false)
    }
  }

  const handleComplete = () => {
    if (summary) {
      onComplete(summary, summary.chief_complaint)
    }
  }

  const handleManualComplete = () => {
    if (messages.length > 2) {
      generateSummary(messages)
    }
  }

  return (
    <div className="voice-collector">
      <div className="voice-header">
        <h3>Voice Symptom Collection</h3>
        <p className="voice-subtitle">
          Speak in any language - I understand Hindi, Tamil, Telugu, Bengali, Marathi, and more
        </p>
        {languageName !== 'English' && (
          <span className="language-badge">Detected: {languageName}</span>
        )}
      </div>

      <div className="voice-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`voice-message ${msg.role}`}>
            <div className="message-avatar">
              {msg.role === 'assistant' ? '🩺' : '👤'}
            </div>
            <div className="message-content">{msg.content}</div>
          </div>
        ))}
        
        {currentTranscript && (
          <div className="voice-message user transcribing">
            <div className="message-avatar">👤</div>
            <div className="message-content">{currentTranscript}</div>
          </div>
        )}
        
        {isProcessing && (
          <div className="voice-message assistant">
            <div className="message-avatar">🩺</div>
            <div className="message-content typing">
              <span></span><span></span><span></span>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {error && (
        <div className="voice-error">{error}</div>
      )}

      {!summary ? (
        <div className="voice-controls">
          <button
            className={`voice-record-btn ${isRecording ? 'recording' : ''}`}
            onMouseDown={startRecording}
            onMouseUp={stopRecording}
            onMouseLeave={stopRecording}
            onTouchStart={startRecording}
            onTouchEnd={stopRecording}
            disabled={isProcessing}
          >
            {isRecording ? (
              <>
                <span className="pulse"></span>
                Release to send
              </>
            ) : isProcessing ? (
              'Processing...'
            ) : (
              <>
                <span className="mic-icon">🎤</span>
                Hold to speak
              </>
            )}
          </button>
          
          <div className="voice-actions">
            {messages.length > 2 && (
              <button 
                className="secondary-btn"
                onClick={handleManualComplete}
                disabled={isGeneratingSummary}
              >
                {isGeneratingSummary ? 'Generating...' : 'Generate Summary'}
              </button>
            )}
            <button className="text-btn" onClick={onCancel}>
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="voice-summary">
          <h4>Symptom Summary</h4>
          
          <div className={`urgency-badge ${summary.recommended_urgency}`}>
            {summary.recommended_urgency === 'emergency' ? '🚨 Emergency' :
             summary.recommended_urgency === 'urgent' ? '⚠️ Urgent' :
             summary.recommended_urgency === 'soon' ? '📅 Schedule Soon' : '✓ Routine'}
          </div>
          
          <div className="summary-section">
            <h5>Chief Complaint</h5>
            <p>{summary.chief_complaint}</p>
          </div>
          
          {summary.symptoms.length > 0 && (
            <div className="summary-section">
              <h5>Symptoms Identified</h5>
              <ul className="symptoms-list">
                {summary.symptoms.map((s, i) => (
                  <li key={i}>
                    <strong>{s.symptom}</strong>
                    {s.duration && <span> - {s.duration}</span>}
                    {s.severity && <span> (Severity: {s.severity})</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          <div className="summary-section">
            <h5>Summary for You</h5>
            <p>{summary.summary_for_patient}</p>
          </div>
          
          {summary.suggested_specialty && (
            <div className="summary-section">
              <h5>Suggested Specialist</h5>
              <p className="specialty-tag">{summary.suggested_specialty}</p>
            </div>
          )}
          
          <div className="summary-actions">
            <button className="primary-btn" onClick={handleComplete}>
              Continue with these symptoms
            </button>
            <button className="secondary-btn" onClick={() => setSummary(null)}>
              Add more details
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

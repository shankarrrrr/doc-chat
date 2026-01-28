import { useState, useRef } from 'react'

type ECGAnalysisProps = {
  accessToken: string | null
  apiUrl: string | undefined
  onAnalysisComplete: () => void
}

type PredictionResult = {
  code: number
  label: string
  message: string
  confidence: number | null
  status: 'normal' | 'attention' | 'critical'
}

export function ECGAnalysis({ accessToken, apiUrl, onAnalysisComplete }: ECGAnalysisProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState<PredictionResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      if (!file.type.startsWith('image/')) {
        setError('Please select an image file (JPEG or PNG)')
        return
      }
      if (file.size > 10 * 1024 * 1024) {
        setError('File size must be less than 10MB')
        return
      }
      setSelectedFile(file)
      setError(null)
      setResult(null)
      
      const reader = new FileReader()
      reader.onloadend = () => {
        setPreview(reader.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleAnalyze = async () => {
    if (!selectedFile || !accessToken || !apiUrl) return

    setAnalyzing(true)
    setError(null)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('ecg_image', selectedFile)

      const res = await fetch(`${apiUrl}/api/ecg/analyze/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      })

      const data = await res.json()

      if (data.success) {
        setResult(data.prediction)
        onAnalysisComplete()
      } else {
        setError(data.error || 'Analysis failed')
      }
    } catch (err) {
      setError('Failed to connect to the server')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleReset = () => {
    setSelectedFile(null)
    setPreview(null)
    setResult(null)
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'normal': return '#10b981'
      case 'attention': return '#f59e0b'
      case 'critical': return '#ef4444'
      default: return '#6b7280'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'normal': return '✓'
      case 'attention': return '⚠'
      case 'critical': return '⚠'
      default: return '?'
    }
  }

  return (
    <div className="ecg-analysis">
      <div className="ecg-analysis-header">
        <span className="ecg-icon">❤️</span>
        <div>
          <h3>ECG Analysis</h3>
          <p>Upload a 12-lead ECG image for cardiovascular disease prediction</p>
        </div>
      </div>

      <div className="ecg-upload-area">
        {!preview ? (
          <label className="ecg-dropzone">
            <input
              type="file"
              ref={fileInputRef}
              accept="image/jpeg,image/png,image/jpg"
              onChange={handleFileSelect}
              hidden
            />
            <span className="upload-icon">📤</span>
            <p className="upload-text">Click to upload ECG image</p>
            <p className="upload-hint">JPEG or PNG, max 10MB</p>
          </label>
        ) : (
          <div className="ecg-preview-container">
            <img src={preview} alt="ECG Preview" className="ecg-preview" />
            <button className="ecg-remove-btn" onClick={handleReset}>×</button>
          </div>
        )}
      </div>

      {error && (
        <div className="ecg-error">
          <span>⚠️</span> {error}
        </div>
      )}

      {result && (
        <div className={`ecg-result status-${result.status}`}>
          <div className="result-header" style={{ borderColor: getStatusColor(result.status) }}>
            <span className="result-icon" style={{ backgroundColor: getStatusColor(result.status) }}>
              {getStatusIcon(result.status)}
            </span>
            <div>
              <h4>{result.label}</h4>
              {result.confidence && (
                <span className="confidence">Confidence: {result.confidence.toFixed(1)}%</span>
              )}
            </div>
          </div>
          <p className="result-message">{result.message}</p>
          {result.status !== 'normal' && (
            <p className="result-warning">
              This is an AI-based screening tool. Please consult a healthcare professional for proper diagnosis.
            </p>
          )}
        </div>
      )}

      <div className="ecg-actions">
        {selectedFile && !result && (
          <button 
            className="primary-btn ecg-analyze-btn" 
            onClick={handleAnalyze}
            disabled={analyzing}
          >
            {analyzing ? (
              <>
                <span className="spinner"></span>
                Analyzing...
              </>
            ) : (
              <>
                <span>🔬</span>
                Analyze ECG
              </>
            )}
          </button>
        )}
        {result && (
          <button className="secondary-btn" onClick={handleReset}>
            Analyze Another ECG
          </button>
        )}
      </div>

      <div className="ecg-info">
        <h4>What can this detect?</h4>
        <ul>
          <li><span className="dot normal"></span> Normal ECG</li>
          <li><span className="dot attention"></span> Abnormal Heartbeat (Arrhythmia)</li>
          <li><span className="dot critical"></span> Myocardial Infarction (Heart Attack)</li>
          <li><span className="dot attention"></span> History of Myocardial Infarction</li>
        </ul>
      </div>
    </div>
  )
}

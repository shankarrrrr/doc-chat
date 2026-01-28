import { useState, useEffect } from 'react'
import type { HealthOnboardingPayload } from './MultiStepOnboarding'

type RecordsPageProps = {
  onboardingData: HealthOnboardingPayload & Record<string, unknown>
  healthSummary: string
  onAddDocuments: () => void
  onConsultDoctor: () => void
  accessToken: string | null
  apiUrl: string | undefined
}

type RecordCategory = 'all' | 'lab_reports' | 'prescriptions' | 'diagnoses' | 'vitals' | 'imaging' | 'other'

type MedicalRecord = {
  id: number
  category: RecordCategory
  title: string
  record_date: string | null
  doctor: string
  facility: string
  summary: string
  details: Record<string, string>
  status: 'normal' | 'attention' | 'critical'
  source_filename: string
  created_at: string
}

const categoryLabels: Record<RecordCategory, string> = {
  all: 'All Records',
  lab_reports: 'Lab Reports',
  prescriptions: 'Prescriptions',
  diagnoses: 'Diagnoses',
  vitals: 'Vitals',
  imaging: 'Imaging',
  other: 'Other',
}

const categoryIcons: Record<RecordCategory, string> = {
  all: '📁',
  lab_reports: '🧪',
  prescriptions: '💊',
  diagnoses: '📋',
  vitals: '❤️',
  imaging: '📷',
  other: '📄',
}

export function RecordsPage({ onboardingData, healthSummary, onAddDocuments, onConsultDoctor, accessToken, apiUrl }: RecordsPageProps) {
  const [selectedCategory, setSelectedCategory] = useState<RecordCategory>('all')
  const [expandedRecord, setExpandedRecord] = useState<number | null>(null)
  const [records, setRecords] = useState<MedicalRecord[]>([])
  const [recordCounts, setRecordCounts] = useState<Record<RecordCategory, number>>({
    all: 0,
    lab_reports: 0,
    prescriptions: 0,
    diagnoses: 0,
    vitals: 0,
    imaging: 0,
    other: 0,
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (accessToken && apiUrl) {
      fetchRecords()
    } else {
      setLoading(false)
    }
  }, [accessToken, apiUrl])

  async function fetchRecords() {
    if (!apiUrl || !accessToken) return
    
    setLoading(true)
    try {
      const res = await fetch(`${apiUrl}/api/records/`, {
        headers: { Authorization: `Bearer ${accessToken}` }
      })
      if (res.ok) {
        const data = await res.json()
        setRecords(data.records || [])
        setRecordCounts(data.counts || {
          all: 0,
          lab_reports: 0,
          prescriptions: 0,
          diagnoses: 0,
          vitals: 0,
          imaging: 0,
          other: 0,
        })
      }
    } catch (e) {
      console.error('Failed to fetch records:', e)
    } finally {
      setLoading(false)
    }
  }

  const filteredRecords = selectedCategory === 'all' 
    ? records 
    : records.filter(r => r.category === selectedCategory)

  const hasUserData = onboardingData && Object.keys(onboardingData).length > 0

  return (
    <div className="records-page">
      <div className="records-header">
        <div className="records-header-content">
          <div>
            <h1 className="records-title">Medical Records</h1>
            <p className="records-subtitle">Your complete health history in one place</p>
          </div>
          <div className="records-header-actions">
            <button className="secondary-btn" onClick={onConsultDoctor}>
              <span>🩺</span> Consult a Doctor
            </button>
            <button className="primary-btn records-add-btn" onClick={onAddDocuments}>
              <span>+</span> Add Documents
            </button>
          </div>
        </div>

        {healthSummary && (
          <div className="records-ai-summary">
            <div className="ai-summary-header">
              <span className="ai-icon">✨</span>
              <h3>AI Health Summary</h3>
            </div>
            <p>{healthSummary}</p>
          </div>
        )}
      </div>

      <div className="records-stats">
        <div className="records-stat-card">
          <span className="stat-icon">📊</span>
          <div>
            <p className="stat-number">{recordCounts.all}</p>
            <p className="stat-text">Total Records</p>
          </div>
        </div>
        <div className="records-stat-card">
          <span className="stat-icon">🧪</span>
          <div>
            <p className="stat-number">{recordCounts.lab_reports}</p>
            <p className="stat-text">Lab Reports</p>
          </div>
        </div>
        <div className="records-stat-card">
          <span className="stat-icon">💊</span>
          <div>
            <p className="stat-number">{recordCounts.prescriptions}</p>
            <p className="stat-text">Prescriptions</p>
          </div>
        </div>
        <div className="records-stat-card">
          <span className="stat-icon">📷</span>
          <div>
            <p className="stat-number">{recordCounts.imaging}</p>
            <p className="stat-text">Imaging</p>
          </div>
        </div>
      </div>

      <div className="records-content">
        <div className="records-sidebar">
          <h3 className="sidebar-title">Categories</h3>
          <div className="category-list">
            {(Object.keys(categoryLabels) as RecordCategory[]).map((cat) => (
              <button
                key={cat}
                className={`category-btn ${selectedCategory === cat ? 'active' : ''}`}
                onClick={() => setSelectedCategory(cat)}
              >
                <span className="category-icon">{categoryIcons[cat]}</span>
                <span className="category-label">{categoryLabels[cat]}</span>
                <span className="category-count">{recordCounts[cat]}</span>
              </button>
            ))}
          </div>

          {hasUserData && (
            <div className="sidebar-section">
              <h3 className="sidebar-title">Quick Info</h3>
              <div className="quick-info">
                {onboardingData.blood_type && (
                  <div className="quick-info-item">
                    <span className="quick-label">Blood Type</span>
                    <span className="quick-value">{String(onboardingData.blood_type)}</span>
                  </div>
                )}
                {onboardingData.allergies && (
                  <div className="quick-info-item">
                    <span className="quick-label">Allergies</span>
                    <span className="quick-value alert">{String(onboardingData.allergies)}</span>
                  </div>
                )}
                {onboardingData.medications && (
                  <div className="quick-info-item">
                    <span className="quick-label">Current Meds</span>
                    <span className="quick-value">{String(onboardingData.medications)}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="records-main">
          <div className="records-list-header">
            <h2>{categoryLabels[selectedCategory]}</h2>
            <span className="record-count">{filteredRecords.length} records</span>
          </div>

          <div className="records-list">
            {loading ? (
              <div className="records-loading">
                <div className="loading-spinner"></div>
                <p>Loading records...</p>
              </div>
            ) : filteredRecords.map((record) => (
              <div 
                key={record.id} 
                className={`record-card ${expandedRecord === record.id ? 'expanded' : ''}`}
                onClick={() => setExpandedRecord(expandedRecord === record.id ? null : record.id)}
              >
                <div className="record-card-main">
                  <div className="record-icon-wrapper">
                    <span className="record-icon">{categoryIcons[record.category] || '📄'}</span>
                  </div>
                  <div className="record-info">
                    <div className="record-title-row">
                      <h3 className="record-title">{record.title}</h3>
                      <span className={`record-status status-${record.status}`}>
                        {record.status === 'normal' ? 'Normal' : record.status === 'attention' ? 'Needs Attention' : 'Critical'}
                      </span>
                    </div>
                    <p className="record-summary">{record.summary || 'No summary available'}</p>
                    <div className="record-meta">
                      <span className="record-date">📅 {record.record_date ? new Date(record.record_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Date not specified'}</span>
                      {record.doctor && <span className="record-doctor">👨‍⚕️ {record.doctor}</span>}
                      {record.facility && <span className="record-facility">🏥 {record.facility}</span>}
                    </div>
                  </div>
                  <button className="record-expand-btn">
                    {expandedRecord === record.id ? '▲' : '▼'}
                  </button>
                </div>

                {expandedRecord === record.id && (
                  <div className="record-details">
                    <h4>Details</h4>
                    <div className="details-grid">
                      {Object.entries(record.details || {}).map(([key, value]) => (
                        <div key={key} className="detail-item">
                          <span className="detail-label">{key}</span>
                          <span className="detail-value">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                    {record.source_filename && (
                      <p className="record-source">Source: {record.source_filename}</p>
                    )}
                    <div className="record-actions">
                      <button className="secondary-btn">Download PDF</button>
                      <button className="secondary-btn">Share with Doctor</button>
                      <button className="primary-btn" onClick={onConsultDoctor}>
                        Consult a Doctor
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {!loading && filteredRecords.length === 0 && (
            <div className="records-empty">
              <span className="empty-icon">📂</span>
              <h3>No records found</h3>
              <p>Upload your medical documents to see them here. AI will automatically categorize and extract information.</p>
              <button className="primary-btn" onClick={onAddDocuments}>Add Documents</button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

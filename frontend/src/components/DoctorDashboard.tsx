import { useState, useEffect } from 'react'

type Patient = {
  id: string
  name: string
  email: string
  age: number | null
  sex: string | null
  conditions: string | null
  current_symptoms: string | null
  assigned_at: string
  notes: string
}

type PatientDetail = {
  patient_info: {
    id: string
    name: string
    email: string
    age: number | null
    sex: string | null
    blood_type: string | null
    location: string | null
  }
  vitals: {
    height: number | null
    weight: number | null
    bmi: number | null
    blood_pressure: string | null
    heart_rate: number | null
    temperature: number | null
    spo2: number | null
  }
  medical_history: {
    conditions: string | null
    medical_history: string | null
    past_reports: string | null
    family_history: string | null
  }
  current_symptoms: {
    current: string | null
    past: string | null
  }
  medications_allergies: {
    current_medications: Array<{ name: string; dosage: string; frequency: string }>
    allergies: Array<{ allergen: string; severity: string; reaction: string }>
    warnings: Array<{ type: string; severity: string; message: string }>
  }
  lifestyle: {
    smoking: string | null
    alcohol: string | null
    exercise: string | null
    diet: string | null
    sleep_hours: number | null
    stress_level: string | null
  }
  emergency_contact: {
    name: string | null
    phone: string | null
  }
  health_goals: string | null
  ai_health_summary: string | null
  symptom_timeline: Array<{
    date: string
    symptom: string
    severity: string
    status: string
    notes: string
  }>
  profile_updated_at: string | null
}

type DoctorDashboardProps = {
  accessToken: string | null
  apiUrl: string | undefined
}

export function DoctorDashboard({ accessToken, apiUrl }: DoctorDashboardProps) {
  const [patients, setPatients] = useState<Patient[]>([])
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null)
  const [patientDetail, setPatientDetail] = useState<PatientDetail | null>(null)
  const [caseSummary, setCaseSummary] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'overview' | 'history' | 'medications' | 'timeline'>('overview')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (accessToken && apiUrl) {
      fetchPatients()
    }
  }, [accessToken, apiUrl])

  async function fetchPatients() {
    if (!apiUrl || !accessToken) return
    setLoading(true)
    try {
      const res = await fetch(`${apiUrl}/api/doctor/patients/`, {
        headers: { Authorization: `Bearer ${accessToken}` }
      })
      if (res.ok) {
        const data = await res.json()
        setPatients(data.patients || [])
      } else {
        setError('Failed to load patients')
      }
    } catch {
      setError('Network error')
    } finally {
      setLoading(false)
    }
  }

  async function fetchPatientDetail(patientId: string) {
    if (!apiUrl || !accessToken) return
    setDetailLoading(true)
    setCaseSummary(null)
    try {
      const res = await fetch(`${apiUrl}/api/doctor/patients/${patientId}/`, {
        headers: { Authorization: `Bearer ${accessToken}` }
      })
      if (res.ok) {
        const data = await res.json()
        setPatientDetail(data)
      }
    } catch {
      setError('Failed to load patient details')
    } finally {
      setDetailLoading(false)
    }
  }

  async function generateCaseSummary() {
    if (!apiUrl || !accessToken || !selectedPatient) return
    setSummaryLoading(true)
    try {
      const res = await fetch(`${apiUrl}/api/doctor/patients/${selectedPatient.id}/summary/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ reason: selectedPatient.current_symptoms || '' })
      })
      if (res.ok) {
        const data = await res.json()
        setCaseSummary(data.summary)
      }
    } catch {
      setError('Failed to generate summary')
    } finally {
      setSummaryLoading(false)
    }
  }

  function handlePatientSelect(patient: Patient) {
    setSelectedPatient(patient)
    fetchPatientDetail(patient.id)
  }

  if (loading) {
    return (
      <div className="doctor-dashboard">
        <div className="doctor-loading">Loading patients...</div>
      </div>
    )
  }

  return (
    <div className="doctor-dashboard">
      {/* Header */}
      <div className="doctor-header">
        <div className="doctor-header-text">
          <h1>Doctor Dashboard</h1>
          <p>Manage your patients and view comprehensive health profiles</p>
        </div>
        <div className="doctor-stats">
          <div className="doctor-stat">
            <span className="doctor-stat-value">{patients.length}</span>
            <span className="doctor-stat-label">Total Patients</span>
          </div>
        </div>
      </div>

      {error && <div className="doctor-error">{error}</div>}

      <div className="doctor-content">
        {/* Patient List */}
        <div className="doctor-sidebar">
          <div className="doctor-sidebar-header">
            <h3>My Patients</h3>
          </div>
          <div className="doctor-patient-list">
            {patients.length === 0 ? (
              <div className="doctor-empty">
                <p>No patients assigned yet</p>
              </div>
            ) : (
              patients.map(patient => (
                <div
                  key={patient.id}
                  className={`doctor-patient-card ${selectedPatient?.id === patient.id ? 'selected' : ''}`}
                  onClick={() => handlePatientSelect(patient)}
                >
                  <div className="doctor-patient-avatar">
                    {patient.name?.charAt(0) || '?'}
                  </div>
                  <div className="doctor-patient-info">
                    <h4>{patient.name || 'Unknown'}</h4>
                    <p>{patient.age ? `${patient.age} yrs` : ''} {patient.sex || ''}</p>
                    {patient.current_symptoms && (
                      <span className="doctor-patient-symptom">{patient.current_symptoms.slice(0, 30)}...</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Patient Detail View */}
        <div className="doctor-main">
          {!selectedPatient ? (
            <div className="doctor-empty-state">
              <div className="doctor-empty-icon">👨‍⚕️</div>
              <h3>Select a Patient</h3>
              <p>Choose a patient from the list to view their comprehensive health profile</p>
            </div>
          ) : detailLoading ? (
            <div className="doctor-loading">Loading patient details...</div>
          ) : patientDetail ? (
            <>
              {/* Patient Header */}
              <div className="doctor-patient-header">
                <div className="doctor-patient-title">
                  <div className="doctor-patient-avatar-large">
                    {patientDetail.patient_info.name?.charAt(0) || '?'}
                  </div>
                  <div>
                    <h2>{patientDetail.patient_info.name}</h2>
                    <p>{patientDetail.patient_info.email}</p>
                  </div>
                </div>
                <button
                  className="doctor-generate-btn"
                  onClick={generateCaseSummary}
                  disabled={summaryLoading}
                >
                  {summaryLoading ? 'Generating...' : '🤖 Generate AI Case Summary'}
                </button>
              </div>

              {/* Quick Stats */}
              <div className="doctor-quick-stats">
                <div className="doctor-quick-stat">
                  <span className="label">Age</span>
                  <span className="value">{patientDetail.patient_info.age || '—'}</span>
                </div>
                <div className="doctor-quick-stat">
                  <span className="label">Sex</span>
                  <span className="value">{patientDetail.patient_info.sex || '—'}</span>
                </div>
                <div className="doctor-quick-stat">
                  <span className="label">Blood Type</span>
                  <span className="value">{patientDetail.patient_info.blood_type || '—'}</span>
                </div>
                <div className="doctor-quick-stat">
                  <span className="label">BMI</span>
                  <span className="value">{patientDetail.vitals.bmi || '—'}</span>
                </div>
              </div>

              {/* AI Case Summary */}
              {caseSummary && (
                <div className="doctor-case-summary">
                  <div className="doctor-case-summary-header">
                    <span className="doctor-case-icon">🤖</span>
                    <h3>AI-Generated Case Summary</h3>
                  </div>
                  <div className="doctor-case-summary-content">
                    {caseSummary.split('\n').map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}
                  </div>
                </div>
              )}

              {/* Tabs */}
              <div className="doctor-tabs">
                {(['overview', 'history', 'medications', 'timeline'] as const).map(tab => (
                  <button
                    key={tab}
                    className={`doctor-tab ${activeTab === tab ? 'active' : ''}`}
                    onClick={() => setActiveTab(tab)}
                  >
                    {tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </button>
                ))}
              </div>

              {/* Tab Content */}
              <div className="doctor-tab-content">
                {activeTab === 'overview' && (
                  <div className="doctor-overview">
                    {/* Current Symptoms */}
                    <div className="doctor-section">
                      <h4>🩺 Current Symptoms</h4>
                      <p>{patientDetail.current_symptoms.current || 'No current symptoms reported'}</p>
                    </div>

                    {/* Vitals */}
                    <div className="doctor-section">
                      <h4>❤️ Vitals</h4>
                      <div className="doctor-vitals-grid">
                        <div className="doctor-vital">
                          <span className="label">Blood Pressure</span>
                          <span className="value">{patientDetail.vitals.blood_pressure || '—'}</span>
                        </div>
                        <div className="doctor-vital">
                          <span className="label">Heart Rate</span>
                          <span className="value">{patientDetail.vitals.heart_rate ? `${patientDetail.vitals.heart_rate} bpm` : '—'}</span>
                        </div>
                        <div className="doctor-vital">
                          <span className="label">SpO2</span>
                          <span className="value">{patientDetail.vitals.spo2 ? `${patientDetail.vitals.spo2}%` : '—'}</span>
                        </div>
                        <div className="doctor-vital">
                          <span className="label">Temperature</span>
                          <span className="value">{patientDetail.vitals.temperature ? `${patientDetail.vitals.temperature}°C` : '—'}</span>
                        </div>
                        <div className="doctor-vital">
                          <span className="label">Height</span>
                          <span className="value">{patientDetail.vitals.height ? `${patientDetail.vitals.height} cm` : '—'}</span>
                        </div>
                        <div className="doctor-vital">
                          <span className="label">Weight</span>
                          <span className="value">{patientDetail.vitals.weight ? `${patientDetail.vitals.weight} kg` : '—'}</span>
                        </div>
                      </div>
                    </div>

                    {/* Lifestyle */}
                    <div className="doctor-section">
                      <h4>🏃 Lifestyle Factors</h4>
                      <div className="doctor-lifestyle-grid">
                        <div className="doctor-lifestyle-item">
                          <span className="label">Smoking</span>
                          <span className="value">{patientDetail.lifestyle.smoking || '—'}</span>
                        </div>
                        <div className="doctor-lifestyle-item">
                          <span className="label">Alcohol</span>
                          <span className="value">{patientDetail.lifestyle.alcohol || '—'}</span>
                        </div>
                        <div className="doctor-lifestyle-item">
                          <span className="label">Exercise</span>
                          <span className="value">{patientDetail.lifestyle.exercise || '—'}</span>
                        </div>
                        <div className="doctor-lifestyle-item">
                          <span className="label">Sleep</span>
                          <span className="value">{patientDetail.lifestyle.sleep_hours ? `${patientDetail.lifestyle.sleep_hours}h` : '—'}</span>
                        </div>
                        <div className="doctor-lifestyle-item">
                          <span className="label">Stress</span>
                          <span className="value">{patientDetail.lifestyle.stress_level || '—'}</span>
                        </div>
                        <div className="doctor-lifestyle-item">
                          <span className="label">Diet</span>
                          <span className="value">{patientDetail.lifestyle.diet || '—'}</span>
                        </div>
                      </div>
                    </div>

                    {/* AI Health Summary */}
                    {patientDetail.ai_health_summary && (
                      <div className="doctor-section">
                        <h4>📋 Patient's AI Health Summary</h4>
                        <p>{patientDetail.ai_health_summary}</p>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'history' && (
                  <div className="doctor-history">
                    <div className="doctor-section">
                      <h4>📁 Medical History</h4>
                      <p>{patientDetail.medical_history.medical_history || 'No medical history recorded'}</p>
                    </div>
                    <div className="doctor-section">
                      <h4>🏥 Conditions</h4>
                      <p>{patientDetail.medical_history.conditions || 'No conditions recorded'}</p>
                    </div>
                    <div className="doctor-section">
                      <h4>📊 Past Reports</h4>
                      <p>{patientDetail.medical_history.past_reports || 'No past reports'}</p>
                    </div>
                    <div className="doctor-section">
                      <h4>👨‍👩‍👧‍👦 Family History</h4>
                      <p>{patientDetail.medical_history.family_history || 'No family history recorded'}</p>
                    </div>
                    <div className="doctor-section">
                      <h4>📝 Past Symptoms</h4>
                      <p>{patientDetail.current_symptoms.past || 'No past symptoms recorded'}</p>
                    </div>
                  </div>
                )}

                {activeTab === 'medications' && (
                  <div className="doctor-medications">
                    {/* Warnings */}
                    {patientDetail.medications_allergies.warnings.length > 0 && (
                      <div className="doctor-warnings">
                        {patientDetail.medications_allergies.warnings.map((warning, i) => (
                          <div key={i} className={`doctor-warning doctor-warning-${warning.severity}`}>
                            ⚠️ {warning.message}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Allergies */}
                    <div className="doctor-section">
                      <h4>🚨 Allergies</h4>
                      {patientDetail.medications_allergies.allergies.length > 0 ? (
                        <div className="doctor-allergy-list">
                          {patientDetail.medications_allergies.allergies.map((allergy, i) => (
                            <div key={i} className="doctor-allergy-item">
                              <span className="allergen">{allergy.allergen}</span>
                              <span className="reaction">{allergy.reaction}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p>No known allergies</p>
                      )}
                    </div>

                    {/* Current Medications */}
                    <div className="doctor-section">
                      <h4>💊 Current Medications</h4>
                      {patientDetail.medications_allergies.current_medications.length > 0 ? (
                        <div className="doctor-medication-list">
                          {patientDetail.medications_allergies.current_medications.map((med, i) => (
                            <div key={i} className="doctor-medication-item">
                              <span className="name">{med.name}</span>
                              <span className="details">{med.dosage} - {med.frequency}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p>No current medications</p>
                      )}
                    </div>
                  </div>
                )}

                {activeTab === 'timeline' && (
                  <div className="doctor-timeline">
                    <h4>📅 Symptom Timeline</h4>
                    {patientDetail.symptom_timeline.length > 0 ? (
                      <div className="doctor-timeline-list">
                        {patientDetail.symptom_timeline.map((event, i) => (
                          <div key={i} className={`doctor-timeline-item doctor-timeline-${event.status}`}>
                            <div className="timeline-marker" />
                            <div className="timeline-content">
                              <div className="timeline-header">
                                <span className="timeline-date">{event.date}</span>
                                <span className={`timeline-severity timeline-severity-${event.severity}`}>
                                  {event.severity}
                                </span>
                              </div>
                              <p className="timeline-symptom">{event.symptom}</p>
                              <p className="timeline-notes">{event.notes}</p>
                              <span className={`timeline-status timeline-status-${event.status}`}>
                                {event.status}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p>No symptom timeline available</p>
                    )}
                  </div>
                )}
              </div>

              {/* Emergency Contact */}
              {(patientDetail.emergency_contact.name || patientDetail.emergency_contact.phone) && (
                <div className="doctor-emergency">
                  <h4>🆘 Emergency Contact</h4>
                  <p><strong>{patientDetail.emergency_contact.name}</strong></p>
                  <p>{patientDetail.emergency_contact.phone}</p>
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}

export default DoctorDashboard

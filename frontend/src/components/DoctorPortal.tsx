import { useState, useEffect, useCallback } from 'react'
import { DoctorLogin } from './DoctorLogin'
import { Line, AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip, PieChart, Pie, Cell } from 'recharts'

type Patient = {
  id: string
  name: string
  email: string
  age: number | null
  sex: string | null
  conditions: string | null
  current_symptoms: string | null
  assigned_at: string
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
}

export function DoctorPortal({ apiUrl }: { apiUrl: string | undefined }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('doctor_token'))

  if (!token) {
    return <DoctorLogin onLogin={(t) => { localStorage.setItem('doctor_token', t); setToken(t) }} apiUrl={apiUrl} />
  }

  return <DoctorDashboard token={token} apiUrl={apiUrl} onLogout={() => { localStorage.removeItem('doctor_token'); setToken(null) }} />
}

// Dummy patient with complete data
const DUMMY_PATIENT: Patient = {
  id: 'demo-patient-001',
  name: 'Sarah Johnson',
  email: 'sarah.johnson@email.com',
  age: 34,
  sex: 'Female',
  conditions: 'Type 2 Diabetes, Hypertension',
  current_symptoms: 'Mild headache, fatigue for 3 days',
  assigned_at: new Date().toISOString()
}

const DUMMY_PATIENT_DETAIL: PatientDetail = {
  patient_info: {
    id: 'demo-patient-001',
    name: 'Sarah Johnson',
    email: 'sarah.johnson@email.com',
    age: 34,
    sex: 'Female',
    blood_type: 'O+',
    location: 'New York, NY'
  },
  vitals: {
    height: 165,
    weight: 68,
    bmi: 25.0,
    blood_pressure: '128/82',
    heart_rate: 78,
    temperature: 36.8,
    spo2: 98
  },
  medical_history: {
    conditions: 'Type 2 Diabetes (diagnosed 2020), Hypertension (diagnosed 2021)',
    medical_history: 'Appendectomy (2015), Gestational diabetes during pregnancy (2018)',
    past_reports: 'HbA1c: 6.8% (March 2024), Cholesterol: 210 mg/dL (March 2024)',
    family_history: 'Father: Heart disease, Mother: Type 2 Diabetes, Grandmother: Stroke'
  },
  current_symptoms: {
    current: 'Mild headache persisting for 3 days, general fatigue, occasional dizziness when standing',
    past: 'Frequent urination (resolved with medication adjustment), Blurred vision (resolved)'
  },
  medications_allergies: {
    current_medications: [
      { name: 'Metformin', dosage: '500mg', frequency: 'Twice daily' },
      { name: 'Lisinopril', dosage: '10mg', frequency: 'Once daily' },
      { name: 'Atorvastatin', dosage: '20mg', frequency: 'Once daily at night' }
    ],
    allergies: [
      { allergen: 'Penicillin', severity: 'Severe', reaction: 'Anaphylaxis' },
      { allergen: 'Sulfa drugs', severity: 'Moderate', reaction: 'Skin rash' }
    ],
    warnings: [
      { type: 'allergy', severity: 'high', message: 'Patient has known allergies: Penicillin (Severe), Sulfa drugs (Moderate)' }
    ]
  },
  lifestyle: {
    smoking: 'Never',
    alcohol: 'Occasional (1-2 drinks/week)',
    exercise: 'Moderate (3x/week)',
    diet: 'Low-carb, diabetic-friendly',
    sleep_hours: 7,
    stress_level: 'Medium'
  },
  emergency_contact: {
    name: 'Michael Johnson (Husband)',
    phone: '+1 (555) 234-5678'
  },
  health_goals: 'Maintain HbA1c below 7%, lose 5kg, improve cardiovascular health',
  ai_health_summary: 'Patient is managing Type 2 Diabetes and Hypertension with medication. Recent lab results show good glycemic control.',
  symptom_timeline: [
    { date: '2024-01-08', symptom: 'Headache started', severity: 'mild', status: 'ongoing', notes: 'Began after stressful work week' },
    { date: '2024-01-09', symptom: 'Fatigue', severity: 'moderate', status: 'ongoing', notes: 'Difficulty concentrating' },
    { date: '2024-01-10', symptom: 'Dizziness', severity: 'mild', status: 'ongoing', notes: 'Occurs when standing quickly' }
  ]
}

function DoctorDashboard({ token, apiUrl, onLogout }: { token: string; apiUrl: string | undefined; onLogout: () => void }) {
  const [patients, setPatients] = useState<Patient[]>([DUMMY_PATIENT])
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(DUMMY_PATIENT)
  const [patientDetail, setPatientDetail] = useState<PatientDetail | null>(DUMMY_PATIENT_DETAIL)
  const [caseSummary, setCaseSummary] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [editMode, setEditMode] = useState(false)
  const [editedVitals, setEditedVitals] = useState<Record<string, string | number>>({
    heart_rate: DUMMY_PATIENT_DETAIL.vitals.heart_rate || '',
    blood_pressure: DUMMY_PATIENT_DETAIL.vitals.blood_pressure || '',
    spo2: DUMMY_PATIENT_DETAIL.vitals.spo2 || '',
    temperature: DUMMY_PATIENT_DETAIL.vitals.temperature || '',
    weight: DUMMY_PATIENT_DETAIL.vitals.weight || '',
    height: DUMMY_PATIENT_DETAIL.vitals.height || '',
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => { 
    fetchPatients()
    // Auto-generate AI summary for dummy patient
    if (selectedPatient?.id === 'demo-patient-001') {
      generateCaseSummary('demo-patient-001', DUMMY_PATIENT_DETAIL.current_symptoms.current || '')
    }
  }, [])

  async function fetchPatients() {
    if (!apiUrl) return
    setLoading(true)
    try {
      const res = await fetch(`${apiUrl}/api/doctor/patients/`, { headers: { Authorization: `Doctor ${token}` } })
      if (res.status === 401) { onLogout(); return }
      if (res.ok) {
        const apiPatients = (await res.json()).patients || []
        setPatients([DUMMY_PATIENT, ...apiPatients])
      }
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const fetchPatientDetail = useCallback(async (patientId: string) => {
    // Handle dummy patient locally
    if (patientId === 'demo-patient-001') {
      setPatientDetail(DUMMY_PATIENT_DETAIL)
      setEditedVitals({
        heart_rate: DUMMY_PATIENT_DETAIL.vitals.heart_rate || '',
        blood_pressure: DUMMY_PATIENT_DETAIL.vitals.blood_pressure || '',
        spo2: DUMMY_PATIENT_DETAIL.vitals.spo2 || '',
        temperature: DUMMY_PATIENT_DETAIL.vitals.temperature || '',
        weight: DUMMY_PATIENT_DETAIL.vitals.weight || '',
        height: DUMMY_PATIENT_DETAIL.vitals.height || '',
      })
      generateCaseSummary(patientId, DUMMY_PATIENT_DETAIL.current_symptoms?.current || '')
      return
    }
    
    if (!apiUrl) return
    setDetailLoading(true)
    setCaseSummary(null)
    try {
      const res = await fetch(`${apiUrl}/api/doctor/patients/${patientId}/`, { headers: { Authorization: `Doctor ${token}` } })
      if (res.ok) {
        const data = await res.json()
        setPatientDetail(data)
        setEditedVitals({
          heart_rate: data.vitals.heart_rate || '',
          blood_pressure: data.vitals.blood_pressure || '',
          spo2: data.vitals.spo2 || '',
          temperature: data.vitals.temperature || '',
          weight: data.vitals.weight || '',
          height: data.vitals.height || '',
        })
        generateCaseSummary(patientId, data.current_symptoms?.current || '')
      }
    } catch (e) { console.error(e) }
    finally { setDetailLoading(false) }
  }, [apiUrl, token])

  async function generateCaseSummary(patientId: string, symptoms: string) {
    // For dummy patient, generate a static summary
    if (patientId === 'demo-patient-001') {
      setSummaryLoading(true)
      setTimeout(() => {
        setCaseSummary(`**PATIENT OVERVIEW**
Sarah Johnson, 34-year-old female presenting with mild headache and fatigue for 3 days.

**CHIEF COMPLAINT**
- Persistent mild headache (3 days)
- General fatigue and difficulty concentrating
- Occasional orthostatic dizziness

**MEDICAL HISTORY SUMMARY**
- Type 2 Diabetes (2020) - well controlled on Metformin
- Hypertension (2021) - managed with Lisinopril
- Previous gestational diabetes (2018)

**CURRENT MEDICATIONS & ALLERGIES**
- Metformin 500mg twice daily
- Lisinopril 10mg once daily
- Atorvastatin 20mg at night
- ALLERGIES: Penicillin (anaphylaxis), Sulfa drugs (rash)

**VITAL SIGNS**
- BP: 128/82 mmHg (slightly elevated)
- HR: 78 bpm (normal)
- SpO2: 98% (normal)
- Temp: 36.8°C (normal)

**SUGGESTED FOCUS AREAS**
- Evaluate headache etiology (tension vs. hypertension-related)
- Check recent blood pressure trends
- Consider blood glucose monitoring
- Assess for signs of postural hypotension

**AI RECOMMENDATIONS**
- Consider 24-hour BP monitoring
- Review medication timing and compliance
- Recommend adequate hydration
- Follow-up HbA1c in 3 months`)
        setSummaryLoading(false)
      }, 1500)
      return
    }
    
    if (!apiUrl) return
    setSummaryLoading(true)
    try {
      const res = await fetch(`${apiUrl}/api/doctor/patients/${patientId}/summary/`, {
        method: 'POST',
        headers: { Authorization: `Doctor ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: symptoms })
      })
      if (res.ok) setCaseSummary((await res.json()).summary)
    } catch (e) { console.error(e) }
    finally { setSummaryLoading(false) }
  }

  async function saveVitals() {
    if (!apiUrl || !selectedPatient) return
    setSaving(true)
    try {
      const res = await fetch(`${apiUrl}/api/doctor/patients/${selectedPatient.id}/update/`, {
        method: 'PUT',
        headers: { Authorization: `Doctor ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          heart_rate: editedVitals.heart_rate ? Number(editedVitals.heart_rate) : null,
          blood_pressure: editedVitals.blood_pressure || null,
          spo2: editedVitals.spo2 ? Number(editedVitals.spo2) : null,
          temperature_c: editedVitals.temperature ? Number(editedVitals.temperature) : null,
          weight: editedVitals.weight ? Number(editedVitals.weight) : null,
          height: editedVitals.height ? Number(editedVitals.height) : null,
        })
      })
      if (res.ok) {
        setPatientDetail(await res.json())
        setEditMode(false)
      }
    } catch (e) { console.error(e) }
    finally { setSaving(false) }
  }

  function handlePatientSelect(patient: Patient) {
    setSelectedPatient(patient)
    setEditMode(false)
    fetchPatientDetail(patient.id)
  }

  const filteredPatients = patients.filter(p =>
    p.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.email?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Chart data
  const vitalTrendData = [
    { name: 'Mon', hr: 72, bp: 120, spo2: 98 },
    { name: 'Tue', hr: 75, bp: 118, spo2: 97 },
    { name: 'Wed', hr: 71, bp: 122, spo2: 98 },
    { name: 'Thu', hr: 78, bp: 125, spo2: 96 },
    { name: 'Fri', hr: 74, bp: 119, spo2: 98 },
    { name: 'Sat', hr: patientDetail?.vitals.heart_rate || 76, bp: 121, spo2: patientDetail?.vitals.spo2 || 97 },
    { name: 'Today', hr: patientDetail?.vitals.heart_rate || 76, bp: 120, spo2: patientDetail?.vitals.spo2 || 98 },
  ]

  const lifestyleData = [
    { name: 'Sleep', value: patientDetail?.lifestyle.sleep_hours || 7, color: '#6366f1' },
    { name: 'Exercise', value: patientDetail?.lifestyle.exercise === 'daily' ? 5 : patientDetail?.lifestyle.exercise === 'weekly' ? 3 : 1, color: '#10b981' },
    { name: 'Stress', value: patientDetail?.lifestyle.stress_level === 'high' ? 8 : patientDetail?.lifestyle.stress_level === 'medium' ? 5 : 2, color: '#f59e0b' },
  ]

  return (
    <div className="doc-portal-v2">
      {/* Header */}
      <header className="doc-header-v2">
        <div className="doc-brand">
          <div className="doc-brand-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></svg>
          </div>
          <div>
            <h1>MedDash</h1>
            <span>Clinical Dashboard</span>
          </div>
        </div>
        <div className="doc-header-actions">
          <div className="doc-stat-badge">
            <span className="doc-stat-num">{patients.length}</span>
            <span>Patients</span>
          </div>
          <button onClick={onLogout} className="doc-btn-ghost">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" /></svg>
          </button>
        </div>
      </header>

      <div className="doc-layout">
        {/* Sidebar */}
        <aside className="doc-sidebar-v2">
          <div className="doc-search-v2">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>
            <input type="text" placeholder="Search patients..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
          </div>
          <div className="doc-patient-list-v2">
            {loading ? (
              <div className="doc-loading-v2"><div className="doc-spinner-v2" /></div>
            ) : filteredPatients.map(p => (
              <div key={p.id} className={`doc-patient-item ${selectedPatient?.id === p.id ? 'active' : ''}`} onClick={() => handlePatientSelect(p)}>
                <div className="doc-patient-avatar-v2">{p.name?.charAt(0).toUpperCase() || '?'}</div>
                <div className="doc-patient-details">
                  <h4>{p.name || 'Unknown'}</h4>
                  <span>{p.age ? `${p.age}y` : ''} {p.sex || ''}</span>
                </div>
                {p.current_symptoms && <div className="doc-patient-status-dot" />}
              </div>
            ))}
          </div>
        </aside>

        {/* Main Content */}
        <main className="doc-main-v2">
          {!selectedPatient ? (
            <div className="doc-empty-state">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
              <h2>Select a Patient</h2>
              <p>Choose a patient from the sidebar to view their complete health profile</p>
            </div>
          ) : detailLoading ? (
            <div className="doc-loading-full-v2"><div className="doc-spinner-v2" /><p>Loading patient data...</p></div>
          ) : patientDetail ? (
            <div className="doc-content-grid">
              {/* Patient Header Card */}
              <div className="doc-card-v2 doc-patient-header-card">
                <div className="doc-patient-profile-v2">
                  <div className="doc-avatar-large">{patientDetail.patient_info.name?.charAt(0).toUpperCase()}</div>
                  <div className="doc-patient-info-v2">
                    <h2>{patientDetail.patient_info.name}</h2>
                    <p>{patientDetail.patient_info.email}</p>
                    <div className="doc-patient-badges">
                      {patientDetail.patient_info.age && <span className="doc-badge">{patientDetail.patient_info.age} years</span>}
                      {patientDetail.patient_info.sex && <span className="doc-badge">{patientDetail.patient_info.sex}</span>}
                      {patientDetail.patient_info.blood_type && <span className="doc-badge doc-badge-red">{patientDetail.patient_info.blood_type}</span>}
                    </div>
                  </div>
                </div>
                <div className="doc-patient-quick-stats">
                  <div className="doc-quick-stat">
                    <span className="doc-quick-stat-value">{patientDetail.vitals.bmi?.toFixed(1) || '--'}</span>
                    <span className="doc-quick-stat-label">BMI</span>
                  </div>
                  <div className="doc-quick-stat">
                    <span className="doc-quick-stat-value">{patientDetail.vitals.weight || '--'}</span>
                    <span className="doc-quick-stat-label">kg</span>
                  </div>
                  <div className="doc-quick-stat">
                    <span className="doc-quick-stat-value">{patientDetail.vitals.height || '--'}</span>
                    <span className="doc-quick-stat-label">cm</span>
                  </div>
                </div>
              </div>

              {/* Vitals Card - Editable */}
              <div className="doc-card-v2 doc-vitals-card">
                <div className="doc-card-header">
                  <h3>Vital Signs</h3>
                  {editMode ? (
                    <div className="doc-edit-actions">
                      <button onClick={() => setEditMode(false)} className="doc-btn-ghost-sm">Cancel</button>
                      <button onClick={saveVitals} disabled={saving} className="doc-btn-primary-sm">{saving ? 'Saving...' : 'Save'}</button>
                    </div>
                  ) : (
                    <button onClick={() => setEditMode(true)} className="doc-btn-ghost-sm">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                      Edit
                    </button>
                  )}
                </div>
                <div className="doc-vitals-grid">
                  <VitalInput label="Heart Rate" unit="bpm" value={editedVitals.heart_rate} onChange={(v) => setEditedVitals({ ...editedVitals, heart_rate: v })} editable={editMode} icon="heart" status={Number(editedVitals.heart_rate) > 100 ? 'warning' : 'normal'} />
                  <VitalInput label="Blood Pressure" unit="mmHg" value={editedVitals.blood_pressure} onChange={(v) => setEditedVitals({ ...editedVitals, blood_pressure: v })} editable={editMode} icon="activity" />
                  <VitalInput label="SpO2" unit="%" value={editedVitals.spo2} onChange={(v) => setEditedVitals({ ...editedVitals, spo2: v })} editable={editMode} icon="droplet" status={Number(editedVitals.spo2) < 95 ? 'warning' : 'normal'} />
                  <VitalInput label="Temperature" unit="°C" value={editedVitals.temperature} onChange={(v) => setEditedVitals({ ...editedVitals, temperature: v })} editable={editMode} icon="thermometer" status={Number(editedVitals.temperature) > 37.5 ? 'warning' : 'normal'} />
                </div>
              </div>

              {/* Vitals Trend Chart */}
              <div className="doc-card-v2 doc-chart-card">
                <div className="doc-card-header">
                  <h3>Vitals Trend (7 Days)</h3>
                  <div className="doc-chart-legend">
                    <span><i style={{ background: '#6366f1' }} />Heart Rate</span>
                    <span><i style={{ background: '#10b981' }} />SpO2</span>
                  </div>
                </div>
                <div className="doc-chart-container">
                  <ResponsiveContainer width="100%" height={180}>
                    <AreaChart data={vitalTrendData}>
                      <defs>
                        <linearGradient id="hrGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} />
                      <YAxis hide domain={[60, 110]} />
                      <Tooltip contentStyle={{ background: '#1e293b', border: 'none', borderRadius: 8, fontSize: 12 }} />
                      <Area type="monotone" dataKey="hr" stroke="#6366f1" fill="url(#hrGrad)" strokeWidth={2} />
                      <Line type="monotone" dataKey="spo2" stroke="#10b981" strokeWidth={2} dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* AI Summary Card - Auto Generated */}
              <div className="doc-card-v2 doc-ai-card">
                <div className="doc-card-header">
                  <h3><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" /></svg> AI Clinical Summary</h3>
                  {summaryLoading && <div className="doc-spinner-sm" />}
                </div>
                <div className="doc-ai-content">
                  {summaryLoading ? (
                    <div className="doc-ai-loading">
                      <div className="doc-ai-skeleton" />
                      <div className="doc-ai-skeleton short" />
                      <div className="doc-ai-skeleton" />
                    </div>
                  ) : caseSummary ? (
                    <div className="doc-ai-text">{caseSummary.split('\n').map((line, i) => {
                      if (line.startsWith('**')) return <h4 key={i}>{line.replace(/\*\*/g, '')}</h4>
                      if (line.startsWith('- ')) return <li key={i}>{line.slice(2)}</li>
                      return line.trim() ? <p key={i}>{line}</p> : null
                    })}</div>
                  ) : <p className="doc-ai-empty">AI summary will appear here...</p>}
                </div>
              </div>

              {/* Current Symptoms */}
              <div className="doc-card-v2 doc-symptoms-card">
                <div className="doc-card-header"><h3>Current Symptoms</h3></div>
                <p className="doc-symptoms-text">{patientDetail.current_symptoms.current || 'No symptoms reported'}</p>
              </div>

              {/* Lifestyle Pie Chart */}
              <div className="doc-card-v2 doc-lifestyle-card">
                <div className="doc-card-header"><h3>Lifestyle Score</h3></div>
                <div className="doc-lifestyle-chart">
                  <ResponsiveContainer width="100%" height={140}>
                    <PieChart>
                      <Pie data={lifestyleData} cx="50%" cy="50%" innerRadius={40} outerRadius={60} paddingAngle={5} dataKey="value">
                        {lifestyleData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="doc-lifestyle-legend">
                    {lifestyleData.map((d, i) => (
                      <div key={i} className="doc-lifestyle-item-v2">
                        <span className="doc-lifestyle-dot" style={{ background: d.color }} />
                        <span>{d.name}</span>
                        <strong>{d.value}</strong>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Medications & Allergies */}
              <div className="doc-card-v2 doc-meds-card">
                <div className="doc-card-header"><h3>Medications & Allergies</h3></div>
                {patientDetail.medications_allergies.warnings.length > 0 && (
                  <div className="doc-alert-banner">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
                    {patientDetail.medications_allergies.warnings[0].message}
                  </div>
                )}
                <div className="doc-meds-grid-v2">
                  <div>
                    <h4>Allergies</h4>
                    {patientDetail.medications_allergies.allergies.length > 0 ? (
                      <ul className="doc-list-v2">
                        {patientDetail.medications_allergies.allergies.map((a, i) => <li key={i} className="doc-list-item-alert">{a.allergen}</li>)}
                      </ul>
                    ) : <p className="doc-muted">None reported</p>}
                  </div>
                  <div>
                    <h4>Current Medications</h4>
                    {patientDetail.medications_allergies.current_medications.length > 0 ? (
                      <ul className="doc-list-v2">
                        {patientDetail.medications_allergies.current_medications.map((m, i) => <li key={i}>{m.name}</li>)}
                      </ul>
                    ) : <p className="doc-muted">None reported</p>}
                  </div>
                </div>
              </div>

              {/* Medical History */}
              <div className="doc-card-v2 doc-history-card">
                <div className="doc-card-header"><h3>Medical History</h3></div>
                <div className="doc-history-grid">
                  <div className="doc-history-item">
                    <span className="doc-history-label">Conditions</span>
                    <p>{patientDetail.medical_history.conditions || 'None'}</p>
                  </div>
                  <div className="doc-history-item">
                    <span className="doc-history-label">Family History</span>
                    <p>{patientDetail.medical_history.family_history || 'None'}</p>
                  </div>
                  <div className="doc-history-item doc-history-full">
                    <span className="doc-history-label">Medical History</span>
                    <p>{patientDetail.medical_history.medical_history || 'None'}</p>
                  </div>
                </div>
              </div>

              {/* Emergency Contact */}
              {(patientDetail.emergency_contact.name || patientDetail.emergency_contact.phone) && (
                <div className="doc-card-v2 doc-emergency-card">
                  <div className="doc-card-header"><h3>Emergency Contact</h3></div>
                  <div className="doc-emergency-info">
                    <strong>{patientDetail.emergency_contact.name}</strong>
                    <span>{patientDetail.emergency_contact.phone}</span>
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </main>
      </div>
    </div>
  )
}

function VitalInput({ label, unit, value, onChange, editable, icon, status = 'normal' }: {
  label: string; unit: string; value: string | number; onChange: (v: string) => void; editable: boolean; icon: string; status?: string
}) {
  const icons: Record<string, React.ReactElement> = {
    heart: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" /></svg>,
    activity: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>,
    droplet: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" /></svg>,
    thermometer: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z" /></svg>,
  }

  return (
    <div className={`doc-vital-input ${status === 'warning' ? 'doc-vital-warning' : ''}`}>
      <div className="doc-vital-icon-v2">{icons[icon]}</div>
      <div className="doc-vital-data">
        <span className="doc-vital-label-v2">{label}</span>
        {editable ? (
          <input type="text" value={value} onChange={(e) => onChange(e.target.value)} className="doc-vital-edit-input" />
        ) : (
          <span className="doc-vital-value-v2">{value || '--'} <small>{unit}</small></span>
        )}
      </div>
    </div>
  )
}

export default DoctorPortal

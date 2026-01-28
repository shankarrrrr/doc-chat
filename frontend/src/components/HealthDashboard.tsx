import type { HealthOnboardingPayload } from './MultiStepOnboarding'
import { buildInsights, buildRecommendations, computeBMI, normalizeOnboardingData, summarizeStatus } from '../lib/healthInsights'

type DashboardProps = {
  user: { name: string | null; email: string | null }
  onboardingRaw: Record<string, unknown>
}

const formatNumber = (value?: number | null, suffix?: string) => {
  if (value === undefined || value === null) return 'Not provided'
  return suffix ? `${value} ${suffix}` : String(value)
}

const fieldText = (value?: string) => value ?? 'Not provided'

export function HealthDashboard({ user, onboardingRaw }: DashboardProps) {
  const data: HealthOnboardingPayload & { symptoms?: string; location?: string } = normalizeOnboardingData(onboardingRaw)
  const status = summarizeStatus(data)
  const bmi = computeBMI(data.height, data.weight)
  const insights = buildInsights(data)
  const recs = buildRecommendations(data)

  return (
    <div className="dashboard-grid">
      <div className="card">
        <span className="pill">Patient Digital Health Profile</span>
        <div className="section-header">
          <div>
            <h2 className="section-title">{data.full_name || user.name || 'Your profile'}</h2>
            <p className="section-subtitle">Unified record of your health details and habits.</p>
          </div>
          <div className={`status-chip status-${status.level}`}>
            {status.level === 'good' ? 'Stable' : status.level === 'watch' ? 'Watch' : 'Action needed'}
          </div>
        </div>

        <div className="stat-grid">
          <div className="stat-card">
            <p className="stat-label">Email</p>
            <p className="stat-value">{user.email ?? 'Not provided'}</p>
          </div>
          <div className="stat-card">
            <p className="stat-label">Age</p>
            <p className="stat-value">{formatNumber(data.age)}</p>
          </div>
          <div className="stat-card">
            <p className="stat-label">Sex</p>
            <p className="stat-value">{fieldText(data.sex)}</p>
          </div>
          <div className="stat-card">
            <p className="stat-label">Height</p>
            <p className="stat-value">{formatNumber(data.height, 'cm')}</p>
          </div>
          <div className="stat-card">
            <p className="stat-label">Weight</p>
            <p className="stat-value">{formatNumber(data.weight, 'kg')}</p>
          </div>
          <div className="stat-card">
            <p className="stat-label">BMI</p>
            <p className="stat-value">{bmi ? bmi : 'Not enough data'}</p>
          </div>
          <div className="stat-card">
            <p className="stat-label">Location</p>
            <p className="stat-value">{fieldText(data.location)}</p>
          </div>
        </div>

        <div className="split-grid">
          <div className="stack">
            <p className="pill">Medical history</p>
            <ul className="detail-list">
              <li><strong>History:</strong> {fieldText(data.medical_history)}</li>
              <li><strong>Past reports & prescriptions:</strong> {fieldText(data.past_reports)}</li>
              <li><strong>Current prescriptions:</strong> {fieldText(data.prescriptions)}</li>
              <li><strong>Conditions:</strong> {fieldText(data.conditions)}</li>
              <li><strong>Medications:</strong> {fieldText(data.medications)}</li>
              <li><strong>Allergies:</strong> {fieldText(data.allergies)}</li>
              <li><strong>Blood type:</strong> {fieldText(data.blood_type)}</li>
              <li><strong>Family history:</strong> {fieldText(data.family_history)}</li>
            </ul>
          </div>
          <div className="stack">
            <p className="pill">Lifestyle</p>
            <ul className="detail-list">
              <li><strong>Exercise:</strong> {fieldText(data.exercise_frequency)}</li>
              <li><strong>Diet:</strong> {fieldText(data.diet_type)}</li>
              <li><strong>Smoking:</strong> {fieldText(data.smoking_status)}</li>
              <li><strong>Alcohol:</strong> {fieldText(data.alcohol_consumption)}</li>
              <li><strong>Sleep:</strong> {data.sleep_hours ? `${data.sleep_hours}h` : 'Not provided'}</li>
              <li><strong>Stress:</strong> {fieldText(data.stress_level)}</li>
            </ul>
          </div>
        </div>

        <div className="split-grid">
          <div className="stack">
            <p className="pill">Symptoms</p>
            <p className="detail-block"><strong>Current:</strong> {fieldText(data.symptoms_current)}</p>
            <p className="detail-block"><strong>Past:</strong> {fieldText(data.symptoms_past)}</p>
          </div>
          <div className="stack">
            <p className="pill">Vitals</p>
            <ul className="detail-list">
              <li><strong>Blood pressure:</strong> {fieldText(data.blood_pressure)}</li>
              <li><strong>Heart rate:</strong> {formatNumber(data.heart_rate, 'bpm')}</li>
              <li><strong>Temperature:</strong> {data.temperature_c !== undefined && data.temperature_c !== null ? `${data.temperature_c}°C` : 'Not provided'}</li>
              <li><strong>SpO₂:</strong> {data.spo2 !== undefined && data.spo2 !== null ? `${data.spo2}%` : 'Not provided'}</li>
            </ul>
          </div>
        </div>

        <div className="split-grid">
          <div className="stack">
            <p className="pill">Goals</p>
            <p className="detail-block">{fieldText(data.health_goals)}</p>
          </div>
          <div className="stack">
            <p className="pill">Emergency contact</p>
            <p className="detail-block">{fieldText(data.emergency_contact_name)}</p>
            <p className="detail-block">{fieldText(data.emergency_contact_phone)}</p>
          </div>
        </div>
      </div>

      <div className="card">
        <span className="pill">AI Health Dashboard</span>
        <h2 className="section-title">Insights</h2>
        <p className="section-subtitle">Is the patient well? Potential issues and next steps.</p>

        <div className="insight-grid">
          {insights.map((insight) => (
            <div key={insight.title} className={`insight-card severity-${insight.severity}`}>
              <div className="insight-head">
                <p className="insight-title">{insight.title}</p>
                <span className={`severity-chip severity-${insight.severity}`}>{insight.severity}</span>
              </div>
              <p className="insight-detail">{insight.detail}</p>
              <p className="insight-action">{insight.action}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <span className="pill">AI Hospital & Doctor Recommender</span>
        <h2 className="section-title">Suggested next clinical steps</h2>
        <p className="section-subtitle">Based on symptoms, history, specialty match, and urgency.</p>

        <div className="recommend-grid">
          {recs.map((rec) => (
            <div key={rec.specialty} className="recommend-card">
              <div className="recommend-head">
                <p className="recommend-title">{rec.title}</p>
                <span className={`severity-chip severity-${rec.urgency}`}>{rec.urgency} urgency</span>
              </div>
              <p className="recommend-meta">Specialty: {rec.specialty}</p>
              <p className="recommend-reason">{rec.reason}</p>
              <p className="recommend-action">Nearest in-network / local options based on your location.</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

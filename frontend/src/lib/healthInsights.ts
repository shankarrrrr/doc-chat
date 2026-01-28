import type { HealthOnboardingPayload } from '../components/MultiStepOnboarding'

export type HealthSnapshot = HealthOnboardingPayload

export type HealthInsight = {
  title: string
  detail: string
  action: string
  severity: 'low' | 'medium' | 'high'
}

export type Recommendation = {
  specialty: string
  title: string
  reason: string
  urgency: 'low' | 'medium' | 'high'
}

const stringVal = (value: unknown): string | undefined => {
  if (typeof value === 'string') return value.trim() || undefined
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  return undefined
}

const numberVal = (value: unknown): number | undefined => {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const num = Number(value.trim())
    if (Number.isFinite(num)) return num
  }
  return undefined
}

export function normalizeOnboardingData(raw: Record<string, unknown> | null | undefined): HealthSnapshot {
  const data = raw ?? {}
  return {
    full_name: stringVal(data.full_name) ?? '',
    age: numberVal(data.age),
    sex: stringVal(data.sex),
    height: numberVal(data.height),
    weight: numberVal(data.weight),
    blood_type: stringVal(data.blood_type),
    allergies: stringVal(data.allergies),
    conditions: stringVal(data.conditions),
    medications: stringVal(data.medications),
    medical_history: stringVal(data.medical_history),
    past_reports: stringVal(data.past_reports),
    prescriptions: stringVal(data.prescriptions),
    symptoms_current: stringVal((data as Record<string, unknown>).symptoms_current),
    symptoms_past: stringVal((data as Record<string, unknown>).symptoms_past),
    location: stringVal((data as Record<string, unknown>).location),
    smoking_status: stringVal(data.smoking_status),
    alcohol_consumption: stringVal(data.alcohol_consumption),
    exercise_frequency: stringVal(data.exercise_frequency),
    diet_type: stringVal(data.diet_type),
    sleep_hours: numberVal(data.sleep_hours),
    stress_level: stringVal(data.stress_level),
    family_history: stringVal(data.family_history),
    health_goals: stringVal(data.health_goals),
    emergency_contact_name: stringVal(data.emergency_contact_name),
    emergency_contact_phone: stringVal(data.emergency_contact_phone),
    blood_pressure: stringVal((data as Record<string, unknown>).blood_pressure),
    heart_rate: numberVal((data as Record<string, unknown>).heart_rate),
    temperature_c: numberVal((data as Record<string, unknown>).temperature_c),
    spo2: numberVal((data as Record<string, unknown>).spo2),
  }
}

export function computeBMI(heightCm?: number, weightKg?: number): number | null {
  if (!heightCm || !weightKg) return null
  const heightM = heightCm / 100
  if (heightM <= 0) return null
  const bmi = weightKg / (heightM * heightM)
  return Number.isFinite(bmi) ? Number(bmi.toFixed(1)) : null
}

const hasKeyword = (text: string | undefined, keywords: string[]): boolean => {
  if (!text) return false
  const lower = text.toLowerCase()
  return keywords.some((k) => lower.includes(k))
}

export function summarizeStatus(data: HealthSnapshot) {
  const bmi = computeBMI(data.height, data.weight)
  let score = 0
  const reasons: string[] = []

  if (bmi) {
    if (bmi >= 30) {
      score += 2
      reasons.push('BMI in obese range')
    } else if (bmi >= 25) {
      score += 1
      reasons.push('BMI in overweight range')
    }
  }

  if (data.sleep_hours !== undefined && data.sleep_hours < 6) {
    score += 1
    reasons.push('Low sleep (<6h)')
  }

  if (data.stress_level === 'high' || data.stress_level === 'very_high') {
    score += 1
    reasons.push('Elevated stress')
  }

  if (data.smoking_status === 'regular') {
    score += 2
    reasons.push('Smoking habit')
  } else if (data.smoking_status === 'occasional' || data.smoking_status === 'former') {
    score += 1
    reasons.push('Smoking history')
  }

  if (data.alcohol_consumption === 'heavy') {
    score += 2
    reasons.push('Heavy alcohol intake')
  } else if (data.alcohol_consumption === 'moderate') {
    score += 1
    reasons.push('Moderate alcohol intake')
  }

  if (data.heart_rate !== undefined && data.heart_rate > 100) {
    score += 1
    reasons.push('Elevated heart rate')
  }

  if (data.temperature_c !== undefined && data.temperature_c >= 37.8) {
    score += 1
    reasons.push('Fever-range temperature')
  }

  if (data.spo2 !== undefined && data.spo2 < 94) {
    score += 1
    reasons.push('Low oxygen saturation')
  }

  if (hasKeyword(data.family_history, ['heart', 'cardiac', 'stroke'])) {
    score += 1
    reasons.push('Cardiovascular family history')
  }

  if (hasKeyword(data.conditions, ['diab', 'hypertension', 'bp', 'blood pressure'])) {
    score += 1
    reasons.push('Chronic condition risk')
  }

  let level: 'good' | 'watch' | 'action' = 'good'
  if (score >= 4) level = 'action'
  else if (score >= 2) level = 'watch'

  const summary =
    level === 'good'
      ? 'Stable baseline with no major red flags detected.'
      : level === 'watch'
        ? 'Some risk factors detected. Monitor and address them proactively.'
        : 'Multiple risk factors detected. Consider clinician follow-up.'

  return { level, summary, bmi, reasons }
}

export function buildInsights(data: HealthSnapshot): HealthInsight[] {
  const insights: HealthInsight[] = []
  const status = summarizeStatus(data)

  insights.push({
    title: 'Overall status',
    detail: status.summary,
    action:
      status.level === 'action'
        ? 'Schedule a clinician review to address the highlighted risks.'
        : status.level === 'watch'
          ? 'Track metrics weekly and adjust lifestyle factors.'
          : 'Maintain current habits and continue periodic check-ins.',
    severity: status.level === 'action' ? 'high' : status.level === 'watch' ? 'medium' : 'low',
  })

  if (status.bmi) {
    const cat = status.bmi >= 30 ? 'obese' : status.bmi >= 25 ? 'overweight' : status.bmi < 18.5 ? 'underweight' : 'healthy'
    const severity: HealthInsight['severity'] = cat === 'healthy' ? 'low' : cat === 'overweight' ? 'medium' : 'high'
    insights.push({
      title: 'Body composition',
      detail: `BMI ${status.bmi} (${cat}).`,
      action:
        cat === 'healthy'
          ? 'Keep balanced nutrition and activity levels.'
          : 'Aim for gradual changes (sleep, nutrition, activity); consider a clinician or dietitian check-in.',
      severity,
    })
  }

  if (data.sleep_hours !== undefined && data.sleep_hours < 7) {
    insights.push({
      title: 'Sleep hygiene',
      detail: `Average sleep ${data.sleep_hours}h — below the 7–9h target.`,
      action: 'Set a regular schedule, reduce caffeine late day, and wind-down 60 minutes before bed.',
      severity: data.sleep_hours < 6 ? 'high' : 'medium',
    })
  }

  if (data.heart_rate !== undefined && data.heart_rate > 100) {
    insights.push({
      title: 'Heart rate',
      detail: `Resting heart rate ${data.heart_rate} bpm — above normal range.`,
      action: 'If persistent, discuss with a clinician; check hydration, caffeine, and stress.',
      severity: 'medium',
    })
  }

  if (data.temperature_c !== undefined && data.temperature_c >= 37.8) {
    insights.push({
      title: 'Fever signal',
      detail: `Temperature ${data.temperature_c}°C.`,
      action: 'Monitor symptoms and seek care if fever persists or worsens.',
      severity: 'medium',
    })
  }

  if (data.spo2 !== undefined && data.spo2 < 94) {
    insights.push({
      title: 'Oxygen saturation',
      detail: `SpO₂ ${data.spo2}% — below typical baseline.`,
      action: 'If symptomatic (e.g., breathlessness), consider urgent evaluation.',
      severity: 'high',
    })
  }

  if (data.symptoms_current) {
    insights.push({
      title: 'Current symptoms',
      detail: data.symptoms_current,
      action: 'Used to triage and tailor recommendations.',
      severity: 'medium',
    })
  }

  if (data.stress_level === 'high' || data.stress_level === 'very_high') {
    insights.push({
      title: 'Stress load',
      detail: `Reported stress: ${data.stress_level?.replace('_', ' ')}`,
      action: 'Integrate brief daily decompression (breathing, walks) and consider speaking with a counselor.',
      severity: 'medium',
    })
  }

  if (data.exercise_frequency && ['sedentary', 'light'].includes(data.exercise_frequency)) {
    insights.push({
      title: 'Activity level',
      detail: `Exercise: ${data.exercise_frequency}.`,
      action: 'Target 150 minutes/week of moderate activity; start with 10–20 minute walks most days.',
      severity: 'medium',
    })
  }

  if (data.smoking_status === 'regular' || data.smoking_status === 'occasional') {
    insights.push({
      title: 'Tobacco risk',
      detail: `Smoking status: ${data.smoking_status}.`,
      action: 'Discuss cessation aids and lung screening timeline with a clinician.',
      severity: data.smoking_status === 'regular' ? 'high' : 'medium',
    })
  }

  if (data.alcohol_consumption === 'heavy' || data.alcohol_consumption === 'moderate') {
    insights.push({
      title: 'Alcohol use',
      detail: `Alcohol intake: ${data.alcohol_consumption}.`,
      action: 'Limit to within recommended guidelines; consider alcohol-free days each week.',
      severity: data.alcohol_consumption === 'heavy' ? 'high' : 'medium',
    })
  }

  if (hasKeyword(data.family_history, ['heart', 'stroke', 'cancer'])) {
    insights.push({
      title: 'Family history flags',
      detail: 'Family history includes cardiovascular or cancer risk.',
      action: 'Share this with your primary doctor; adhere to screening intervals earlier where indicated.',
      severity: 'medium',
    })
  }

  if (data.conditions) {
    insights.push({
      title: 'Chronic conditions',
      detail: `Reported: ${data.conditions}.`,
      action: 'Ensure medications are reconciled and monitoring plans are in place.',
      severity: 'medium',
    })
  }

  return insights
}

export function buildRecommendations(data: HealthSnapshot): Recommendation[] {
  const recs: Recommendation[] = []

  const add = (rec: Recommendation) => {
    if (!recs.find((r) => r.specialty === rec.specialty)) recs.push(rec)
  }

  const symptoms = data.symptoms_current ?? data.conditions ?? data.symptoms_past ?? ''

  if (
    hasKeyword(symptoms, ['chest pain', 'shortness of breath', 'palpitations']) ||
    hasKeyword(data.family_history, ['heart', 'cardiac']) ||
    hasKeyword(data.conditions, ['hypertension'])
  ) {
    add({
      specialty: 'Cardiology',
      title: 'Cardiology consult',
      reason: 'Cardio risk signals (symptoms or family history).',
      urgency: hasKeyword(symptoms, ['chest pain', 'shortness of breath']) ? 'high' : 'medium',
    })
  }

  if (hasKeyword(symptoms, ['cough', 'wheez', 'asthma']) || data.smoking_status === 'regular') {
    add({
      specialty: 'Pulmonology',
      title: 'Lung health review',
      reason: 'Respiratory symptoms or smoking history.',
      urgency: data.smoking_status === 'regular' ? 'medium' : 'low',
    })
  }

  if (hasKeyword(symptoms, ['blood sugar', 'glucose']) || hasKeyword(data.conditions, ['diab'])) {
    add({
      specialty: 'Endocrinology',
      title: 'Metabolic check',
      reason: 'Metabolic flags (diabetes or glucose concerns).',
      urgency: 'medium',
    })
  }

  if (data.stress_level === 'high' || data.stress_level === 'very_high') {
    add({
      specialty: 'Behavioral Health',
      title: 'Stress & mood support',
      reason: 'Elevated stress reported.',
      urgency: 'medium',
    })
  }

  return recs.slice(0, 4)
}

import { describe, expect, it } from 'vitest'
import { buildInsights, buildRecommendations, computeBMI, normalizeOnboardingData, summarizeStatus } from './healthInsights'

describe('healthInsights helpers', () => {
  it('computes BMI from height/weight', () => {
    expect(computeBMI(180, 81)).toBe(25)
    expect(computeBMI(undefined, 81)).toBeNull()
  })

  it('normalizes onboarding data', () => {
    const normalized = normalizeOnboardingData({
      full_name: ' Jane ',
      age: '30',
      height: '170',
      symptoms_current: 'cough',
      location: 'Mumbai',
      heart_rate: '110',
      temperature_c: '38.2',
      unknown: 'x',
    })
    expect(normalized.full_name).toBe('Jane')
    expect(normalized.age).toBe(30)
    expect(normalized.height).toBe(170)
    expect(normalized.weight).toBeUndefined()
    expect(normalized.symptoms_current).toBe('cough')
    expect(normalized.location).toBe('Mumbai')
    expect(normalized.heart_rate).toBe(110)
    expect(normalized.temperature_c).toBe(38.2)
  })

  it('summarizes status with multiple risk factors', () => {
    const status = summarizeStatus({
      full_name: 'Test',
      height: 170,
      weight: 95,
      sleep_hours: 5,
      stress_level: 'high',
      smoking_status: 'regular',
      alcohol_consumption: 'moderate',
    })

    expect(status.level).toBe('action')
    expect(status.reasons).toContain('BMI in obese range')
    expect(status.reasons).toContain('Low sleep (<6h)')
  })

  it('builds insights and recommendations from data', () => {
    const data = normalizeOnboardingData({
      conditions: 'hypertension',
      family_history: 'heart disease',
      smoking_status: 'regular',
      sleep_hours: 6,
      stress_level: 'high',
      symptoms_current: 'chest pain',
      location: 'Mumbai',
    })

    const insights = buildInsights(data)
    expect(insights.some((i) => i.title === 'Overall status')).toBe(true)
    expect(insights.some((i) => i.title === 'Current symptoms')).toBe(true)

    const recs = buildRecommendations(data)
    expect(recs.some((r) => r.specialty === 'Cardiology')).toBe(true)
    expect(recs.some((r) => r.specialty === 'Primary Care')).toBe(false)
  })
})

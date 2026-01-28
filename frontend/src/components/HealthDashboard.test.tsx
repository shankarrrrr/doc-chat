import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { HealthDashboard } from './HealthDashboard'

const user = { name: 'Jane Doe', email: 'jane@example.com' }

const onboardingRaw = {
  full_name: 'Jane Doe',
  age: 32,
  sex: 'female',
  height: 170,
  weight: 70,
  blood_type: 'O+',
  medical_history: 'Diabetes type 2',
  past_reports: 'HbA1c 7.2%',
  prescriptions: 'Metformin 500mg BID',
  conditions: 'Hypertension',
  allergies: 'Penicillin',
  symptoms_current: 'Chest pain and shortness of breath',
  symptoms_past: 'Occasional dizziness',
  location: 'Mumbai',
  heart_rate: 105,
  temperature_c: 37.9,
  spo2: 93,
  exercise_frequency: 'light',
  diet_type: 'vegetarian',
  smoking_status: 'regular',
  alcohol_consumption: 'moderate',
  sleep_hours: 6,
  stress_level: 'high',
}

describe('HealthDashboard', () => {
  it('renders key patient profile fields and AI recommendations', () => {
    render(<HealthDashboard user={user} onboardingRaw={onboardingRaw} />)

    expect(screen.getByText(/Patient Digital Health Profile/i)).toBeTruthy()
    expect(screen.getAllByText(/Chest pain and shortness of breath/i)[0]).toBeTruthy()
    expect(screen.getByText(/Cardiology consult/i)).toBeTruthy()
    expect(screen.getByText(/AI Health Dashboard/i)).toBeTruthy()
    expect(screen.getByText(/SpO₂ 93%/i)).toBeTruthy()
  })
})

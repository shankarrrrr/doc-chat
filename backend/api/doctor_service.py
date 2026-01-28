import requests
from django.conf import settings
from typing import Optional
from datetime import datetime, timedelta

GEMINI_MODEL = 'gemini-2.0-flash'


def generate_ai_case_summary(patient_data: dict, appointment_reason: str = '') -> str:
    """Generate AI case summary for doctor using Gemini."""
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == 'your_gemini_api_key_here':
        return 'AI summarization unavailable - API key not configured.'

    url = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}'

    prompt = f"""You are a medical AI assistant helping doctors prepare for patient consultations.
Generate a comprehensive case summary for the doctor based on the patient data below.

PATIENT DATA:
{_format_patient_data(patient_data)}

APPOINTMENT REASON: {appointment_reason if appointment_reason else 'General consultation'}

Generate a structured case summary with the following sections:

1. **PATIENT OVERVIEW**: Brief patient profile (age, gender, key identifiers)

2. **CHIEF COMPLAINT**: Current symptoms and reason for visit

3. **MEDICAL HISTORY SUMMARY**: 
   - Relevant past conditions
   - Chronic conditions
   - Previous surgeries/procedures

4. **CURRENT MEDICATIONS & ALLERGIES**:
   - Active medications with dosages
   - Known allergies (HIGHLIGHT any drug allergies)

5. **SYMPTOM TIMELINE**:
   - When symptoms started
   - Progression of symptoms
   - Any triggers identified

6. **VITAL SIGNS & RECENT LAB VALUES**:
   - Latest vitals if available
   - Any abnormal values (FLAG these)

7. **RISK FACTORS**:
   - Lifestyle factors (smoking, alcohol, exercise)
   - Family history
   - BMI and related risks

8. **SUGGESTED FOCUS AREAS**:
   - Key areas to investigate
   - Recommended questions to ask
   - Potential differential diagnoses to consider

9. **AI RECOMMENDATIONS** (for doctor's consideration):
   - Suggested tests or referrals
   - Treatment considerations based on guidelines

Keep the summary concise but comprehensive. Use bullet points for readability.
Highlight any critical or urgent findings.
"""

    try:
        response = requests.post(
            url,
            json={
                'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
                'generationConfig': {
                    'temperature': 0.3,
                    'maxOutputTokens': 2048,
                }
            },
            timeout=60
        )

        if response.ok:
            data = response.json()
            text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text')
            return text if text else 'Failed to generate summary.'
        else:
            return f'AI service error: {response.status_code}'
    except Exception as e:
        return f'AI service unavailable: {str(e)}'


def generate_symptom_timeline(patient_data: dict) -> list:
    """Extract and structure symptom timeline from patient data."""
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == 'your_gemini_api_key_here':
        return _fallback_symptom_timeline(patient_data)

    url = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}'

    prompt = f"""Analyze the patient data and extract a symptom timeline.

PATIENT DATA:
{_format_patient_data(patient_data)}

Return a JSON array of symptom events with this structure:
[
    {{
        "date": "YYYY-MM-DD or relative time like '2 weeks ago'",
        "symptom": "symptom description",
        "severity": "mild|moderate|severe",
        "status": "ongoing|resolved|improved",
        "notes": "any additional context"
    }}
]

Only include actual symptoms mentioned in the data.
Return ONLY the JSON array, no other text."""

    try:
        response = requests.post(
            url,
            json={
                'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
                'generationConfig': {
                    'temperature': 0.2,
                    'maxOutputTokens': 1024,
                }
            },
            timeout=30
        )

        if response.ok:
            import json
            data = response.json()
            text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '[]')
            text = text.strip()
            if text.startswith('```'):
                text = text.split('\n', 1)[1] if '\n' in text else text[3:]
            if text.endswith('```'):
                text = text[:-3]
            return json.loads(text.strip())
    except Exception:
        pass
    
    return _fallback_symptom_timeline(patient_data)


def generate_medication_overview(patient_data: dict) -> dict:
    """Generate structured medication and allergy overview."""
    medications = patient_data.get('medications') or patient_data.get('prescriptions') or ''
    allergies = patient_data.get('allergies', '')
    
    return {
        'current_medications': _parse_medications(medications),
        'allergies': _parse_allergies(allergies),
        'drug_interactions': [],  # Could be enhanced with drug interaction API
        'warnings': _generate_medication_warnings(medications, allergies)
    }


def get_patient_dashboard_data(profile) -> dict:
    """Get comprehensive patient data for doctor dashboard."""
    onboarding_data = profile.onboarding_data or {}
    
    # Calculate BMI if height and weight available
    bmi = None
    height = onboarding_data.get('height')
    weight = onboarding_data.get('weight')
    if height and weight:
        try:
            height_m = float(height) / 100
            bmi = round(float(weight) / (height_m ** 2), 1)
        except (ValueError, ZeroDivisionError):
            pass
    
    return {
        'patient_info': {
            'id': str(profile.supabase_uid),
            'name': profile.full_name,
            'email': profile.email,
            'age': onboarding_data.get('age'),
            'sex': onboarding_data.get('sex'),
            'blood_type': onboarding_data.get('blood_type'),
            'location': onboarding_data.get('location'),
        },
        'vitals': {
            'height': onboarding_data.get('height'),
            'weight': onboarding_data.get('weight'),
            'bmi': bmi,
            'blood_pressure': onboarding_data.get('blood_pressure'),
            'heart_rate': onboarding_data.get('heart_rate'),
            'temperature': onboarding_data.get('temperature_c'),
            'spo2': onboarding_data.get('spo2'),
        },
        'medical_history': {
            'conditions': onboarding_data.get('conditions'),
            'medical_history': onboarding_data.get('medical_history'),
            'past_reports': onboarding_data.get('past_reports'),
            'family_history': onboarding_data.get('family_history'),
        },
        'current_symptoms': {
            'current': onboarding_data.get('symptoms_current'),
            'past': onboarding_data.get('symptoms_past'),
        },
        'medications_allergies': generate_medication_overview(onboarding_data),
        'lifestyle': {
            'smoking': onboarding_data.get('smoking_status'),
            'alcohol': onboarding_data.get('alcohol_consumption'),
            'exercise': onboarding_data.get('exercise_frequency'),
            'diet': onboarding_data.get('diet_type'),
            'sleep_hours': onboarding_data.get('sleep_hours'),
            'stress_level': onboarding_data.get('stress_level'),
        },
        'emergency_contact': {
            'name': onboarding_data.get('emergency_contact_name'),
            'phone': onboarding_data.get('emergency_contact_phone'),
        },
        'health_goals': onboarding_data.get('health_goals'),
        'ai_health_summary': profile.health_summary,
        'symptom_timeline': generate_symptom_timeline(onboarding_data),
        'profile_updated_at': profile.updated_at.isoformat() if profile.updated_at else None,
    }


def _format_patient_data(data: dict) -> str:
    """Format patient data for AI prompt."""
    lines = []
    for key, value in data.items():
        if value:
            formatted_key = key.replace('_', ' ').title()
            lines.append(f"- {formatted_key}: {value}")
    return '\n'.join(lines) if lines else 'No data available'


def _fallback_symptom_timeline(patient_data: dict) -> list:
    """Fallback symptom timeline when AI is not available."""
    timeline = []
    current_symptoms = patient_data.get('symptoms_current')
    past_symptoms = patient_data.get('symptoms_past')
    
    if current_symptoms:
        timeline.append({
            'date': 'Current',
            'symptom': current_symptoms,
            'severity': 'unknown',
            'status': 'ongoing',
            'notes': 'Current symptoms as reported'
        })
    
    if past_symptoms:
        timeline.append({
            'date': 'Past',
            'symptom': past_symptoms,
            'severity': 'unknown',
            'status': 'resolved',
            'notes': 'Historical symptoms'
        })
    
    return timeline


def _parse_medications(medications_str: str) -> list:
    """Parse medication string into structured list."""
    if not medications_str:
        return []
    
    meds = []
    for med in medications_str.split(','):
        med = med.strip()
        if med:
            meds.append({
                'name': med,
                'dosage': 'Not specified',
                'frequency': 'Not specified'
            })
    return meds


def _parse_allergies(allergies_str: str) -> list:
    """Parse allergies string into structured list."""
    if not allergies_str:
        return []
    
    allergies = []
    for allergy in allergies_str.split(','):
        allergy = allergy.strip()
        if allergy:
            allergies.append({
                'allergen': allergy,
                'severity': 'unknown',
                'reaction': 'Not specified'
            })
    return allergies


def _generate_medication_warnings(medications: str, allergies: str) -> list:
    """Generate basic medication warnings."""
    warnings = []
    
    if allergies:
        warnings.append({
            'type': 'allergy',
            'severity': 'high',
            'message': f'Patient has known allergies: {allergies}'
        })
    
    return warnings

import requests
from django.conf import settings

GEMINI_MODEL = 'gemini-2.0-flash'


def get_specialty_recommendations(onboarding_data: dict) -> list[dict]:
    """Use Gemini to analyze patient data and recommend medical specialties."""
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == 'your_gemini_api_key_here':
        return get_fallback_recommendations(onboarding_data)

    url = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}'

    patient_context = f"""
Patient Data:
- Age: {onboarding_data.get('age', 'Unknown')}
- Gender: {onboarding_data.get('sex', 'Unknown')}
- Current Symptoms: {onboarding_data.get('symptoms_current', 'None reported')}
- Past Symptoms: {onboarding_data.get('symptoms_past', 'None')}
- Medical History: {onboarding_data.get('medical_history', 'None')}
- Conditions: {onboarding_data.get('conditions', 'None')}
- Medications: {onboarding_data.get('medications') or onboarding_data.get('prescriptions', 'None')}
- Allergies: {onboarding_data.get('allergies', 'None')}
- Family History: {onboarding_data.get('family_history', 'None')}
- Vitals: BP {onboarding_data.get('blood_pressure', 'N/A')}, HR {onboarding_data.get('heart_rate', 'N/A')} bpm
"""

    prompt = f"""Based on this patient's health profile, recommend which medical specialists they should consult.

{patient_context}

Return a JSON array with up to 4 specialty recommendations. Each should have:
- "specialty": The medical specialty (e.g., "Cardiologist", "General Physician", "Orthopedic")
- "search_term": Google Maps search term (e.g., "cardiologist", "general physician clinic", "orthopedic doctor")
- "reason": Brief reason for this recommendation (1 sentence)
- "urgency": "low", "medium", or "high"
- "priority": 1-4 (1 being most important)

If no specific symptoms, recommend General Physician first.
ONLY return valid JSON array, no markdown or explanation."""

    try:
        response = requests.post(
            url,
            json={
                'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
                'generationConfig': {
                    'temperature': 0.3,
                    'maxOutputTokens': 1024,
                }
            },
            timeout=30
        )

        if response.ok:
            data = response.json()
            text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '[]')
            text = text.strip()
            if text.startswith('```'):
                text = text.split('\n', 1)[1] if '\n' in text else text[3:]
            if text.endswith('```'):
                text = text[:-3]
            
            import json
            recommendations = json.loads(text.strip())
            if isinstance(recommendations, list):
                return sorted(recommendations, key=lambda x: x.get('priority', 99))[:4]
    except Exception as e:
        print(f'Gemini recommendation error: {e}')

    return get_fallback_recommendations(onboarding_data)


def get_fallback_recommendations(onboarding_data: dict) -> list[dict]:
    """Fallback recommendations when Gemini is unavailable."""
    recs = []
    symptoms = (onboarding_data.get('symptoms_current', '') or '').lower()
    conditions = (onboarding_data.get('conditions', '') or '').lower()

    recs.append({
        'specialty': 'General Physician',
        'search_term': 'general physician clinic',
        'reason': 'Primary care for overall health assessment and referrals.',
        'urgency': 'medium',
        'priority': 1
    })

    if any(k in symptoms for k in ['chest', 'heart', 'breath', 'palpitation']) or 'hypertension' in conditions:
        recs.append({
            'specialty': 'Cardiologist',
            'search_term': 'cardiologist',
            'reason': 'Cardiovascular symptoms or conditions detected.',
            'urgency': 'high',
            'priority': 1
        })

    if any(k in symptoms for k in ['joint', 'bone', 'back', 'knee', 'spine']):
        recs.append({
            'specialty': 'Orthopedic',
            'search_term': 'orthopedic doctor',
            'reason': 'Musculoskeletal symptoms reported.',
            'urgency': 'medium',
            'priority': 2
        })

    if any(k in symptoms for k in ['skin', 'rash', 'itch', 'acne']):
        recs.append({
            'specialty': 'Dermatologist',
            'search_term': 'dermatologist',
            'reason': 'Skin-related symptoms reported.',
            'urgency': 'low',
            'priority': 3
        })

    return recs[:4]


def geocode_location(location: str) -> dict | None:
    """Convert location string to lat/lng using Google Geocoding API."""
    api_key = settings.GOOGLE_MAPS_API_KEY
    if not api_key:
        return None

    try:
        response = requests.get(
            'https://maps.googleapis.com/maps/api/geocode/json',
            params={
                'address': location,
                'key': api_key
            },
            timeout=10
        )
        if response.ok:
            data = response.json()
            if data.get('results'):
                loc = data['results'][0]['geometry']['location']
                return {'lat': loc['lat'], 'lng': loc['lng']}
    except Exception as e:
        print(f'Geocoding error: {e}')

    return None


def search_nearby_places(lat: float, lng: float, search_term: str, radius: int = 10000) -> list[dict]:
    """Search for nearby hospitals/doctors using Google Places API."""
    api_key = settings.GOOGLE_MAPS_API_KEY
    if not api_key:
        return []

    try:
        response = requests.get(
            'https://maps.googleapis.com/maps/api/place/nearbysearch/json',
            params={
                'location': f'{lat},{lng}',
                'radius': radius,
                'keyword': search_term,
                'type': 'hospital|doctor|health',
                'key': api_key
            },
            timeout=15
        )
        if response.ok:
            data = response.json()
            results = []
            for place in data.get('results', [])[:5]:
                results.append({
                    'place_id': place.get('place_id'),
                    'name': place.get('name'),
                    'address': place.get('vicinity'),
                    'rating': place.get('rating'),
                    'user_ratings_total': place.get('user_ratings_total', 0),
                    'lat': place['geometry']['location']['lat'],
                    'lng': place['geometry']['location']['lng'],
                    'open_now': place.get('opening_hours', {}).get('open_now'),
                    'types': place.get('types', []),
                })
            return results
    except Exception as e:
        print(f'Places search error: {e}')

    return []


def get_place_details(place_id: str) -> dict | None:
    """Get detailed info about a place."""
    api_key = settings.GOOGLE_MAPS_API_KEY
    if not api_key:
        return None

    try:
        response = requests.get(
            'https://maps.googleapis.com/maps/api/place/details/json',
            params={
                'place_id': place_id,
                'fields': 'name,formatted_address,formatted_phone_number,website,opening_hours,rating,reviews,url',
                'key': api_key
            },
            timeout=10
        )
        if response.ok:
            data = response.json()
            result = data.get('result', {})
            return {
                'name': result.get('name'),
                'address': result.get('formatted_address'),
                'phone': result.get('formatted_phone_number'),
                'website': result.get('website'),
                'google_maps_url': result.get('url'),
                'rating': result.get('rating'),
                'opening_hours': result.get('opening_hours', {}).get('weekday_text', []),
            }
    except Exception as e:
        print(f'Place details error: {e}')

    return None


def get_full_recommendations(onboarding_data: dict, user_lat: float = None, user_lng: float = None) -> dict:
    """Get complete recommendations with nearby places."""
    specialty_recs = get_specialty_recommendations(onboarding_data)
    
    location = onboarding_data.get('location', '')
    coords = None
    
    if user_lat and user_lng:
        coords = {'lat': user_lat, 'lng': user_lng}
    elif location:
        coords = geocode_location(location)

    result = {
        'specialties': specialty_recs,
        'location': coords,
        'places': {}
    }

    if coords:
        for rec in specialty_recs:
            search_term = rec.get('search_term', rec['specialty'])
            places = search_nearby_places(coords['lat'], coords['lng'], search_term)
            result['places'][rec['specialty']] = places

    return result

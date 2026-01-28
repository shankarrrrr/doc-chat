"""
AI Service using Google Generative AI (google-generativeai package)

Models:
- gemini-2.5-pro: For chatbot conversations (more capable)
- gemini-2.5-flash: For document parsing and other tasks (faster)
"""

import json
import requests
import google.generativeai as genai
from django.conf import settings

# Model configuration
CHATBOT_MODEL = 'gemini-2.5-pro'
UTILITY_MODEL = 'gemini-2.5-flash'

SYSTEM_PROMPT = """You are a helpful AI health assistant. You have access to the patient's health profile and should provide personalized health advice, answer medical questions, and help them understand their health better.

IMPORTANT GUIDELINES:
1. Always be empathetic and supportive
2. Provide evidence-based health information
3. Recommend consulting a doctor for serious concerns
4. Never diagnose conditions definitively - suggest possibilities and recommend professional consultation
5. Consider the patient's specific health data when giving advice
6. Keep responses concise but informative
7. If asked about medications, remind them to consult their doctor before making changes"""


def configure_genai():
    """Configure the Google Generative AI with API key."""
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == 'your_gemini_api_key_here':
        raise Exception('Gemini API key not configured')
    genai.configure(api_key=api_key)


def build_patient_context(onboarding_data: dict, health_summary: str = '', medical_records: list = None) -> str:
    if not onboarding_data:
        onboarding_data = {}

    data = onboarding_data
    context = f"""
PATIENT PROFILE:
- Name: {data.get('full_name', 'Not provided')}
- Age: {data.get('age', 'Not provided')}
- Gender: {data.get('sex', 'Not provided')}
- Location: {data.get('location', 'Not provided')}

VITALS:
- Height: {f"{data.get('height')} cm" if data.get('height') else 'Not provided'}
- Weight: {f"{data.get('weight')} kg" if data.get('weight') else 'Not provided'}
- Blood Pressure: {data.get('blood_pressure', 'Not provided')}
- Heart Rate: {f"{data.get('heart_rate')} bpm" if data.get('heart_rate') else 'Not provided'}
- Temperature: {f"{data.get('temperature_c')}°C" if data.get('temperature_c') else 'Not provided'}
- SpO2: {f"{data.get('spo2')}%" if data.get('spo2') else 'Not provided'}

MEDICAL HISTORY:
- Past Conditions: {data.get('medical_history', 'Not provided')}
- Past Reports: {data.get('past_reports', 'Not provided')}
- Current Prescriptions: {data.get('prescriptions', 'Not provided')}
- Allergies: {data.get('allergies', 'Not provided')}
- Blood Type: {data.get('blood_type', 'Not provided')}

CURRENT SYMPTOMS:
- Current: {data.get('symptoms_current', 'None reported')}
- Past Symptoms: {data.get('symptoms_past', 'None reported')}

LIFESTYLE:
- Exercise: {data.get('exercise_frequency', 'Not provided')}
- Diet: {data.get('diet_type', 'Not provided')}
- Sleep: {f"{data.get('sleep_hours')} hours" if data.get('sleep_hours') else 'Not provided'}
- Stress Level: {data.get('stress_level', 'Not provided')}
"""

    # Add health summary from parsed documents
    if health_summary:
        context += f"""
AI-GENERATED HEALTH SUMMARY (from uploaded medical documents):
{health_summary}
"""

    # Add medical records
    if medical_records:
        context += """
MEDICAL RECORDS (from uploaded documents):
"""
        for record in medical_records[:20]:  # Limit to 20 most recent records
            context += f"""
- [{record.get('category', 'other').upper()}] {record.get('title', 'Unknown')}
  Summary: {record.get('summary', 'No summary')}
  Status: {record.get('status', 'unknown')}
  Date: {record.get('record_date', 'Unknown')}
  Details: {json.dumps(record.get('details', {})) if record.get('details') else 'None'}
"""

    return context.strip()


def call_gemini_api(messages: list, patient_context: str) -> str:
    """Call Gemini API for chatbot using gemini-2.5-pro."""
    configure_genai()
    
    model = genai.GenerativeModel(
        model_name=CHATBOT_MODEL,
        generation_config={
            'temperature': 0.7,
            'top_p': 0.95,
            'top_k': 40,
            'max_output_tokens': 10000,
        },
        safety_settings=[
            {'category': 'HARM_CATEGORY_HARASSMENT', 'threshold': 'BLOCK_NONE'},
            {'category': 'HARM_CATEGORY_HATE_SPEECH', 'threshold': 'BLOCK_NONE'},
            {'category': 'HARM_CATEGORY_SEXUALLY_EXPLICIT', 'threshold': 'BLOCK_NONE'},
            {'category': 'HARM_CATEGORY_DANGEROUS_CONTENT', 'threshold': 'BLOCK_NONE'},
        ],
        system_instruction=f"{SYSTEM_PROMPT}\n\n{patient_context}"
    )
    
    # Build chat history
    history = []
    for msg in messages[:-1]:  # All except the last message
        history.append({
            'role': 'user' if msg['role'] == 'user' else 'model',
            'parts': [msg['content']]
        })
    
    chat = model.start_chat(history=history)
    
    # Send the last message
    last_message = messages[-1]['content'] if messages else "Hello"
    response = chat.send_message(last_message)
    
    return response.text


def call_utility_model(prompt: str, max_tokens: int = 2048, temperature: float = 0.3) -> str:
    """Call Gemini utility model (gemini-2.5-flash) for parsing and other tasks."""
    configure_genai()
    
    model = genai.GenerativeModel(
        model_name=UTILITY_MODEL,
        generation_config={
            'temperature': temperature,
            'max_output_tokens': max_tokens,
        }
    )
    
    response = model.generate_content(prompt)
    return response.text


def call_decodo_fallback(messages: list, patient_context: str) -> str:
    """Fallback to Decodo if Gemini fails."""
    import requests
    
    auth_token = settings.DECODO_AUTH_TOKEN
    if not auth_token:
        raise Exception('Decodo auth token not configured')

    last_user_message = ''
    for msg in reversed(messages):
        if msg['role'] == 'user':
            last_user_message = msg['content']
            break

    conversation_history = '\n'.join([
        f"{'Patient' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in messages[:-1]
    ])

    prompt = f"""You are a health assistant. Here is the patient's data:
{patient_context}

Previous conversation:
{conversation_history}

Patient's question: {last_user_message}

Please provide helpful health advice based on this information."""

    response = requests.post(
        'https://scraper-api.decodo.com/v2/scrape',
        headers={
            'accept': 'application/json',
            'content-type': 'application/json',
            'authorization': auth_token
        },
        json={
            'target': 'chatgpt',
            'prompt': prompt,
            'search': True,
            'geo': 'India',
            'markdown': True
        },
        timeout=30
    )

    if not response.ok:
        raise Exception(f'Decodo API error: {response.status_code}')

    data = response.json()
    content = data.get('results', [{}])[0].get('content') or data.get('content') or ''
    
    if 'ChatGPT said:' in content:
        parts = content.split('ChatGPT said:')
        if len(parts) > 1:
            ai_response = parts[-1]
            for stop_marker in ['Sources', 'By messaging ChatGPT', 'Citations', '- More', 'Try Go, Free']:
                if stop_marker in ai_response:
                    ai_response = ai_response.split(stop_marker)[0]
            content = ai_response.strip()
    
    return content if content else 'Sorry, I could not generate a response.'


def parse_document_with_gemini(documents: list, current_data: dict, current_summary: str = '') -> dict:
    """Parse medical documents and extract health information using Gemini."""
    configure_genai()
    
    model = genai.GenerativeModel(
        model_name=UTILITY_MODEL,
        generation_config={
            'temperature': 0.2,
            'max_output_tokens': 2048,
        }
    )
    
    instruction = f"""You are a medical document parser. Analyze the provided medical documents (prescriptions, lab reports, medical records, appointment notes) and extract relevant health information.

CURRENT PATIENT SUMMARY (update this with new findings):
{current_summary if current_summary else 'No previous summary available.'}

Extract and return a JSON object with these fields:
{{
    "medical_history": "past medical conditions found",
    "past_reports": "summary of lab results or diagnostic reports",
    "prescriptions": "current medications and dosages",
    "symptoms_current": "any current symptoms mentioned",
    "blood_pressure": "blood pressure reading if found (e.g., '120/80')",
    "heart_rate": "heart rate in bpm if found",
    "temperature_c": "temperature in Celsius if found",
    "spo2": "oxygen saturation percentage if found",
    "blood_type": "blood type if mentioned",
    "allergies": "any allergies mentioned",
    "conditions": "diagnosed conditions",
    "doctor_notes": "any doctor's observations, recommendations, or conclusions",
    "diagnosis": "any diagnosis made by the doctor",
    "treatment_plan": "recommended treatments or follow-up actions",
    "health_summary": "A comprehensive 2-3 paragraph summary of the patient's overall health condition based on ALL documents and previous summary."
}}

IMPORTANT: 
- Only return valid JSON, no markdown or explanation
- Only include fields where you found actual data
- Be concise but accurate
- The health_summary MUST be included and should be comprehensive"""

    # Build content parts
    parts = [instruction]
    
    for doc in documents:
        if doc['type'] == 'image':
            import base64
            parts.append({
                'mime_type': doc['mime_type'],
                'data': doc['data']
            })
            parts.append(f"[Image: {doc['name']}]")
        else:
            parts.append(f"Document: {doc['name']}\n{doc['content'][:10000]}")

    response = model.generate_content(parts)
    text = response.text.strip()
    
    # Clean up markdown if present
    if text.startswith('```'):
        text = text.split('\n', 1)[1] if '\n' in text else text[3:]
    if text.endswith('```'):
        text = text[:-3]
    text = text.strip()
    
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except:
        return {}


def parse_document_to_records(documents: list, current_summary: str = '') -> dict:
    """Parse medical documents and extract individual medical records with categorization."""
    configure_genai()
    
    model = genai.GenerativeModel(
        model_name=UTILITY_MODEL,
        generation_config={
            'temperature': 0.2,
            'max_output_tokens': 4096,
        }
    )
    
    instruction = f"""You are a medical document parser. Analyze the provided medical documents and extract INDIVIDUAL medical records.

CURRENT PATIENT SUMMARY (to be updated):
{current_summary if current_summary else 'No previous summary available.'}

For EACH distinct medical record found in the documents, extract and categorize it.

Return a JSON object with this structure:
{{
    "records": [
        {{
            "category": "lab_reports|prescriptions|diagnoses|vitals|imaging|other",
            "title": "Name/title of the record (e.g., 'Complete Blood Count', 'Metformin 500mg', 'Chest X-Ray')",
            "summary": "Brief description of findings or purpose",
            "details": {{"key": "value"}} - specific measurements, dosages, or findings,
            "doctor": "Doctor's name if mentioned",
            "facility": "Hospital/clinic name if mentioned",
            "record_date": "YYYY-MM-DD format if date is found, null otherwise",
            "status": "normal|attention|critical" - based on findings
        }}
    ],
    "health_summary": "Updated comprehensive 2-3 paragraph summary of patient's overall health including these new findings.",
    "profile_updates": {{
        "blood_pressure": "value if found",
        "heart_rate": "value if found",
        "allergies": "any allergies found",
        "blood_type": "if found",
        "medications": "current medications list"
    }}
}}

CATEGORIZATION GUIDE:
- lab_reports: Blood tests, urine tests, pathology reports, metabolic panels
- prescriptions: Medications, drug prescriptions, pharmacy orders
- diagnoses: Disease diagnoses, medical conditions, clinical assessments
- vitals: Blood pressure, heart rate, temperature, weight, height, SpO2
- imaging: X-rays, MRI, CT scans, ultrasounds, mammograms, ECG/EKG images (electrocardiograms)
- other: Appointment notes, referrals, general medical documents

ECG ANALYSIS (if ECG/EKG image is detected):
When analyzing an ECG image, look for:
- Heart rhythm (normal sinus rhythm, arrhythmia, atrial fibrillation, etc.)
- Heart rate (calculate from R-R intervals)
- ST segment changes (elevation/depression indicating ischemia or MI)
- T wave abnormalities
- QRS complex width
- PR interval
- Signs of: Myocardial Infarction (MI), Left/Right Bundle Branch Block, Ventricular Hypertrophy
- Any other cardiac abnormalities visible in the 12-lead ECG
Set status to "critical" if signs of acute MI or dangerous arrhythmia, "attention" for any abnormalities, "normal" for healthy ECG.

STATUS GUIDE:
- normal: Values within normal range, routine findings
- attention: Slightly abnormal values, requires monitoring
- critical: Significantly abnormal, requires immediate attention

IMPORTANT:
- Only return valid JSON, no markdown
- Extract EACH distinct record as a separate item
- Be specific with titles"""

    # Build content parts
    parts = [instruction]
    
    for doc in documents:
        if doc['type'] == 'image':
            parts.append({
                'mime_type': doc['mime_type'],
                'data': doc['data']
            })
            parts.append(f"[Image: {doc['name']}]")
        else:
            parts.append(f"Document: {doc['name']}\n{doc['content'][:10000]}")

    response = model.generate_content(parts)
    text = response.text.strip()
    
    # Clean up markdown if present
    if text.startswith('```'):
        text = text.split('\n', 1)[1] if '\n' in text else text[3:]
    if text.endswith('```'):
        text = text[:-3]
    text = text.strip()
    
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {'records': [], 'health_summary': '', 'profile_updates': {}}
    except:
        return {'records': [], 'health_summary': '', 'profile_updates': {}}


def get_ai_response(messages: list, onboarding_data: dict, health_summary: str = '', medical_records: list = None) -> str:
    """Main function to get AI response for chat."""
    patient_context = build_patient_context(onboarding_data, health_summary, medical_records)

    # Step 1: Try Gemini first (primary)
    gemini_key = settings.GEMINI_API_KEY
    if gemini_key and gemini_key != 'your_gemini_api_key_here':
        try:
            return call_gemini_api(messages, patient_context)
        except Exception as e:
            print(f'Gemini failed, trying Decodo fallback: {e}')

    # Step 2: Fallback to Decodo if Gemini failed
    if settings.DECODO_AUTH_TOKEN:
        try:
            return call_decodo_fallback(messages, patient_context)
        except Exception as e:
            print(f'Decodo fallback also failed: {e}')

    raise Exception('AI services are unavailable. Please try again later.')

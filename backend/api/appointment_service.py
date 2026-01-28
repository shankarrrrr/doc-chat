"""
Twilio-based AI Appointment Booking Service

This service handles:
1. Initiating outbound calls to hospitals
2. Using Gemini AI (gemini-2.5-flash) to conduct the conversation
3. Extracting appointment details from the conversation
4. Updating appointment records with confirmed details
"""

import json
import re
import google.generativeai as genai
from datetime import datetime, date, time
from typing import Optional
from django.conf import settings

# Model for appointment calls (use flash for speed)
APPOINTMENT_MODEL = 'gemini-2.0-flash'


def configure_genai():
    """Configure the Google Generative AI with API key."""
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == 'your_gemini_api_key_here':
        raise Exception('Gemini API key not configured')
    genai.configure(api_key=api_key)


def get_twilio_client():
    """Get configured Twilio client."""
    from twilio.rest import Client
    
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    
    if not account_sid or not auth_token:
        raise ValueError("Twilio credentials not configured")
    
    account_sid = account_sid.strip("'\"")
    auth_token = auth_token.strip("'\"")
    
    return Client(account_sid, auth_token)


def get_phone_number_to_call(hospital_phone: str) -> str:
    """
    Get the phone number to call.
    In development, uses TEST_PHONE_NUMBER to avoid calling real hospitals.
    """
    test_number = settings.TEST_PHONE_NUMBER
    if test_number:
        return test_number.strip("'\"")
    return hospital_phone


def call_gemini_for_appointment(prompt: str, max_tokens: int = 2048) -> str:
    """Call Gemini API for appointment-related tasks using gemini-2.5-flash."""
    configure_genai()
    
    model = genai.GenerativeModel(
        model_name=APPOINTMENT_MODEL,
        generation_config={
            'temperature': 0.7,
            'max_output_tokens': max_tokens,
        }
    )
    
    response = model.generate_content(prompt)
    return response.text


def generate_ai_response(hospital_name: str, patient_info: dict, 
                         purpose: str, conversation_history: list,
                         hospital_response: str = None,
                         is_initial: bool = False) -> str:
    """
    Generate AI response for the phone conversation using Gemini.
    """
    patient_name = patient_info.get('full_name', 'Patient')
    patient_age = patient_info.get('age', 'Not specified')
    symptoms = patient_info.get('symptoms_current', purpose) or purpose or 'General consultation'
    
    if is_initial:
        prompt = f"""You are an AI assistant making a phone call to {hospital_name} to book a medical appointment.

Patient Details:
- Name: {patient_name}
- Age: {patient_age}
- Symptoms: {symptoms}

Generate ONLY the opening statement. Be polite and professional.
Keep it to 2-3 sentences. Include:
1. Greeting and that you're calling on behalf of the patient
2. Mention the symptoms/reason for visit
3. Request to book an appointment

Response (just the spoken text, nothing else):"""
    else:
        history_text = "\n".join([
            f"{'Hospital' if i % 2 == 0 else 'You'}: {msg}" 
            for i, msg in enumerate(conversation_history)
        ])
        
        prompt = f"""You are an AI assistant on a phone call with {hospital_name} booking an appointment.

Patient Details:
- Name: {patient_name}
- Age: {patient_age}
- Reason for visit: {symptoms}

Conversation so far:
{history_text}

Hospital just said: "{hospital_response}"

Generate your next response. Be concise and professional.
If they offer an appointment slot, accept it and confirm the details.
If they ask for information, provide it from the patient details.
If the appointment is confirmed, thank them and say goodbye.

Your response (just the spoken text, nothing else):"""
    
    try:
        return call_gemini_for_appointment(prompt)
    except Exception as e:
        print(f"Gemini API error in call: {e}")
        if is_initial:
            return f"Hello, I am calling on behalf of {patient_name} to book an appointment. Could you please help me with that?"
        return "Yes, please proceed. What time slots do you have available?"


def extract_appointment_details(transcript: str, hospital_name: str) -> dict:
    """
    Use Gemini to extract appointment details from the call transcript.
    """
    prompt = f"""Analyze this phone call transcript where someone is booking a hospital appointment at {hospital_name}.

Transcript:
{transcript}

Extract the following information if mentioned. Return a JSON object with these fields:
- appointment_confirmed: boolean (true if appointment was successfully booked)
- appointment_date: string in YYYY-MM-DD format (or null if not mentioned)
- appointment_time: string in HH:MM format 24-hour (or null if not mentioned)
- doctor_name: string (or null if not mentioned)
- department: string (or null if not mentioned)
- notes: string with any other relevant information

Return ONLY the JSON object, no other text:"""

    try:
        result_text = call_gemini_for_appointment(prompt)
        
        if result_text.startswith('```'):
            result_text = re.sub(r'^```json?\n?', '', result_text)
            result_text = re.sub(r'\n?```$', '', result_text)
        
        return json.loads(result_text)
        
    except Exception as e:
        print(f"Error extracting appointment details: {e}")
        return {}


def simulate_appointment_booking(appointment_id: int, patient_info: dict) -> dict:
    """
    Simulate an appointment booking for testing without actual Twilio call.
    Uses Gemini to simulate the conversation.
    """
    from .models import Appointment
    import time as time_module
    import random
    
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        appointment.status = 'calling'
        appointment.save()
        
        time_module.sleep(2)
        
        patient_name = patient_info.get('full_name', 'Patient')
        symptoms = patient_info.get('symptoms_current', appointment.purpose) or 'General consultation'
        
        prompt = f"""Simulate a realistic phone conversation between an AI assistant and a hospital receptionist.
The AI is calling {appointment.hospital_name} to book an appointment.

Patient: {patient_name}
Reason: {symptoms}

Generate a complete conversation that ends with a confirmed appointment.
Include realistic details like:
- Available time slots
- Doctor's name
- Department
- Any instructions

Format each line as:
AI: [what AI says]
Receptionist: [what receptionist says]

End with a confirmed appointment date and time (use dates within the next 2 weeks from today {date.today().strftime('%Y-%m-%d')}).

Conversation:"""
        
        transcript = call_gemini_for_appointment(prompt)
        appointment.call_transcript = transcript
        
        details = extract_appointment_details(transcript, appointment.hospital_name)
        
        if details.get('appointment_confirmed', True):
            appointment.status = 'confirmed'
            
            if details.get('appointment_date'):
                try:
                    appointment.appointment_date = datetime.strptime(
                        details['appointment_date'], '%Y-%m-%d'
                    ).date()
                except:
                    from datetime import timedelta
                    appointment.appointment_date = date.today() + timedelta(days=random.randint(2, 14))
            else:
                from datetime import timedelta
                appointment.appointment_date = date.today() + timedelta(days=random.randint(2, 14))
            
            if details.get('appointment_time'):
                try:
                    appointment.appointment_time = datetime.strptime(
                        details['appointment_time'], '%H:%M'
                    ).time()
                except:
                    appointment.appointment_time = time(10, 30)
            else:
                appointment.appointment_time = time(random.randint(9, 16), random.choice([0, 30]))
            
            appointment.doctor_name = details.get('doctor_name') or 'Dr. Available'
            appointment.department = details.get('department') or 'General Medicine'
            appointment.notes = details.get('notes') or 'Appointment confirmed via AI call'
            appointment.call_duration = random.randint(60, 180)
        else:
            appointment.status = 'failed'
            appointment.notes = 'Could not confirm appointment in simulation'
        
        appointment.save()
        
        return {
            'success': True,
            'status': appointment.status,
            'appointment_date': str(appointment.appointment_date) if appointment.appointment_date else None,
            'appointment_time': str(appointment.appointment_time) if appointment.appointment_time else None,
            'doctor_name': appointment.doctor_name,
            'department': appointment.department,
            'transcript': transcript
        }
        
    except Exception as e:
        print(f"Simulation error: {e}")
        try:
            appointment = Appointment.objects.get(id=appointment_id)
            appointment.status = 'failed'
            appointment.notes = f'Simulation failed: {str(e)}'
            appointment.save()
        except:
            pass
        
        return {
            'success': False,
            'error': str(e),
            'status': 'failed'
        }


# ============ Twilio Call Functions (for real calls) ============

def initiate_appointment_call(appointment_id: int, hospital_phone: str, 
                              patient_info: dict, purpose: str,
                              callback_url: str) -> dict:
    """
    Initiate an outbound call to the hospital for appointment booking.
    """
    from .models import Appointment
    from twilio.twiml.voice_response import VoiceResponse, Gather
    
    try:
        client = get_twilio_client()
        phone_to_call = get_phone_number_to_call(hospital_phone)
        from_number = settings.TWILIO_PHONE_NUMBER.strip("'\"")
        
        appointment = Appointment.objects.get(id=appointment_id)
        appointment.status = 'calling'
        appointment.save()
        
        response = VoiceResponse()
        
        gather = Gather(
            input='speech',
            action=f'{callback_url}/api/appointments/call-response/{appointment_id}/',
            method='POST',
            speech_timeout='auto',
            language='en-IN'
        )
        
        initial_message = generate_ai_response(
            appointment.hospital_name,
            patient_info,
            purpose,
            [],
            is_initial=True
        )
        
        gather.say(initial_message, voice='Polly.Aditi', language='en-IN')
        response.append(gather)
        
        response.say("I didn't receive a response. Let me try again.", 
                    voice='Polly.Aditi', language='en-IN')
        response.redirect(f'{callback_url}/api/appointments/call-retry/{appointment_id}/')
        
        call = client.calls.create(
            twiml=str(response),
            to=phone_to_call,
            from_=from_number,
            status_callback=f'{callback_url}/api/appointments/call-status/{appointment_id}/',
            status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
            status_callback_method='POST'
        )
        
        appointment.call_sid = call.sid
        appointment.save()
        
        return {
            'success': True,
            'call_sid': call.sid,
            'status': 'calling',
            'message': f'Call initiated to {phone_to_call}'
        }
        
    except Exception as e:
        try:
            appointment = Appointment.objects.get(id=appointment_id)
            appointment.status = 'failed'
            appointment.notes = f'Call initiation failed: {str(e)}'
            appointment.save()
        except:
            pass
        
        return {
            'success': False,
            'error': str(e),
            'status': 'failed'
        }


def process_call_response(appointment_id: int, speech_result: str, 
                          callback_url: str) -> str:
    """
    Process the hospital's response and generate the next AI response.
    """
    from .models import Appointment
    from twilio.twiml.voice_response import VoiceResponse, Gather
    
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        
        patient_info = appointment.profile.onboarding_data or {}
        patient_info['full_name'] = appointment.profile.full_name
        
        current_transcript = appointment.call_transcript or ''
        current_transcript += f"\nHospital: {speech_result}"
        
        history = [line.split(': ', 1)[1] for line in current_transcript.strip().split('\n') if ': ' in line]
        
        # Check if appointment seems confirmed from speech
        speech_lower = speech_result.lower()
        confirmation_keywords = ['confirmed', 'booked', 'scheduled', 'appointment is', 'see you', 'tomorrow at', 'today at', 'available at']
        appointment_confirmed_in_speech = any(kw in speech_lower for kw in confirmation_keywords)
        
        end_keywords = ['goodbye', 'thank you', 'have a nice day', 'bye']
        should_end = any(kw in speech_lower for kw in end_keywords) or appointment_confirmed_in_speech
        
        ai_response = generate_ai_response(
            appointment.hospital_name,
            patient_info,
            appointment.purpose,
            history,
            hospital_response=speech_result,
            is_initial=False
        )
        
        current_transcript += f"\nAI: {ai_response}"
        appointment.call_transcript = current_transcript
        appointment.save()
        
        response = VoiceResponse()
        
        ai_lower = ai_response.lower()
        ai_ends_call = 'goodbye' in ai_lower or 'thank you' in ai_lower or 'bye' in ai_lower
        
        if should_end or ai_ends_call:
            response.say(ai_response, voice='Polly.Aditi', language='en-IN')
            response.hangup()
            
            # Extract details - use simpler regex-based extraction for speed
            details = extract_appointment_details_fast(current_transcript)
            
            # If we detected confirmation keywords, mark as confirmed
            if appointment_confirmed_in_speech or details.get('appointment_confirmed'):
                appointment.status = 'confirmed'
                appointment.appointment_date = details.get('appointment_date')
                appointment.appointment_time = details.get('appointment_time')
                appointment.doctor_name = details.get('doctor_name', '')
                appointment.department = details.get('department', 'General Medicine')
                appointment.notes = 'Appointment confirmed via AI call'
            else:
                appointment.status = 'failed'
                appointment.notes = 'Appointment could not be confirmed'
            
            appointment.save()
        else:
            gather = Gather(
                input='speech',
                action=f'{callback_url}/api/appointments/call-response/{appointment_id}/',
                method='POST',
                speech_timeout='auto',
                language='en-IN'
            )
            gather.say(ai_response, voice='Polly.Aditi', language='en-IN')
            response.append(gather)
            
            response.say("I didn't catch that. Could you please repeat?",
                        voice='Polly.Aditi', language='en-IN')
            response.redirect(f'{callback_url}/api/appointments/call-retry/{appointment_id}/')
        
        return str(response)
        
    except Exception as e:
        import traceback
        print(f"Error processing call response: {e}")
        traceback.print_exc()
        
        # Try to mark appointment as failed
        try:
            from .models import Appointment
            appointment = Appointment.objects.get(id=appointment_id)
            appointment.status = 'failed'
            appointment.notes = f'Call error: {str(e)}'
            appointment.save()
        except:
            pass
        
        from twilio.twiml.voice_response import VoiceResponse
        response = VoiceResponse()
        response.say("I apologize, there was a technical issue. Thank you for your time. Goodbye.", 
                    voice='Polly.Aditi', language='en-IN')
        response.hangup()
        return str(response)


def extract_appointment_details_fast(transcript: str) -> dict:
    """
    Fast regex-based extraction of appointment details.
    Avoids slow Gemini API call for real-time response.
    """
    import re
    from datetime import timedelta
    
    result = {
        'appointment_confirmed': False,
        'appointment_date': None,
        'appointment_time': None,
        'doctor_name': '',
        'department': 'General Medicine'
    }
    
    transcript_lower = transcript.lower()
    
    # Check for confirmation
    if any(kw in transcript_lower for kw in ['confirmed', 'booked', 'scheduled', 'appointment is set']):
        result['appointment_confirmed'] = True
    
    # Extract doctor name
    doctor_match = re.search(r'(?:dr\.?|doctor)\s+([a-zA-Z]+)', transcript, re.IGNORECASE)
    if doctor_match:
        result['doctor_name'] = f"Dr. {doctor_match.group(1).title()}"
    
    # Extract time
    time_match = re.search(r'(\d{1,2})[:\s]?(\d{2})?\s*(a\.?m\.?|p\.?m\.?)', transcript, re.IGNORECASE)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        period = time_match.group(3).lower().replace('.', '')
        
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        
        result['appointment_time'] = time(hour, minute)
    
    # Extract date - look for "tomorrow", "today", or specific dates
    if 'tomorrow' in transcript_lower:
        result['appointment_date'] = date.today() + timedelta(days=1)
        result['appointment_confirmed'] = True
    elif 'today' in transcript_lower:
        result['appointment_date'] = date.today()
        result['appointment_confirmed'] = True
    elif 'day after tomorrow' in transcript_lower:
        result['appointment_date'] = date.today() + timedelta(days=2)
        result['appointment_confirmed'] = True
    
    return result


def update_call_status(appointment_id: int, call_status: str, 
                       call_duration: int = None) -> None:
    """
    Update appointment based on Twilio call status callback.
    """
    from .models import Appointment
    
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        
        if call_duration:
            appointment.call_duration = call_duration
        
        if call_status == 'completed':
            if appointment.status == 'calling':
                appointment.status = 'failed'
                appointment.notes = 'Call ended without confirmation'
        elif call_status in ['busy', 'no-answer', 'failed', 'canceled']:
            appointment.status = 'failed'
            appointment.notes = f'Call {call_status}'
        
        appointment.save()
        
    except Exception as e:
        print(f"Error updating call status: {e}")

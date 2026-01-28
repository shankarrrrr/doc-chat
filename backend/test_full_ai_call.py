"""
Test script for FULL AI appointment booking call with webhooks.
This will call you and have a multi-turn conversation.
YOU act as the hospital receptionist.
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings
from api.models import Profile, Appointment
from api.appointment_service import generate_ai_response, get_phone_number_to_call
from twilio.rest import Client
import uuid


def make_full_ai_call():
    """Make a full AI appointment booking call with webhooks."""
    print("=" * 60)
    print("FULL AI APPOINTMENT BOOKING CALL")
    print("=" * 60)
    
    # Get credentials
    account_sid = settings.TWILIO_ACCOUNT_SID.strip("'\"")
    auth_token = settings.TWILIO_AUTH_TOKEN.strip("'\"")
    from_number = settings.TWILIO_PHONE_NUMBER.strip("'\"")
    to_number = settings.TEST_PHONE_NUMBER.strip("'\"")
    ngrok_url = settings.NGROK_URL.strip("'\"")
    
    print(f"From: {from_number}")
    print(f"To: {to_number}")
    print(f"Webhook URL: {ngrok_url}")
    
    if not ngrok_url:
        print("\n[ERROR] NGROK_URL not set in .env!")
        return
    
    # Create test profile
    test_uid = uuid.uuid4()
    profile, _ = Profile.objects.get_or_create(
        email='ai_call_test@example.com',
        defaults={
            'supabase_uid': test_uid,
            'full_name': 'Rahul Sharma',
            'onboarding_completed': True,
            'onboarding_data': {
                'full_name': 'Rahul Sharma',
                'age': 28,
                'symptoms_current': 'Fever and severe headache for 3 days'
            }
        }
    )
    
    # Create appointment
    appointment = Appointment.objects.create(
        profile=profile,
        hospital_name='City General Hospital',
        hospital_phone='+919876543210',
        hospital_address='123 Medical Street, Mumbai',
        purpose='Fever and severe headache for 3 days'
    )
    
    print(f"\nAppointment ID: {appointment.id}")
    print(f"Patient: {profile.full_name}")
    print(f"Hospital: {appointment.hospital_name}")
    print(f"Purpose: {appointment.purpose}")
    
    # Generate initial message
    patient_info = profile.onboarding_data or {}
    patient_info['full_name'] = profile.full_name
    
    initial_message = generate_ai_response(
        hospital_name=appointment.hospital_name,
        patient_info=patient_info,
        purpose=appointment.purpose,
        conversation_history=[],
        is_initial=True
    )
    
    print(f"\nAI will say: {initial_message}")
    
    # Update appointment status
    appointment.status = 'calling'
    appointment.call_transcript = f"AI: {initial_message}"
    appointment.save()
    
    # Create Twilio client
    client = Client(account_sid, auth_token)
    
    # Webhook URL for handling responses
    webhook_url = f"{ngrok_url}/api/appointments/call-response/{appointment.id}/"
    status_url = f"{ngrok_url}/api/appointments/call-status/{appointment.id}/"
    
    print(f"\nWebhook URL: {webhook_url}")
    
    # TwiML with Gather for speech input - NO "I am listening", just waits for response
    twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Aditi" language="en-IN">{initial_message}</Say>
    <Gather input="speech" timeout="8" speechTimeout="auto" language="en-IN" action="{webhook_url}" method="POST">
    </Gather>
    <Say voice="Polly.Aditi" language="en-IN">I did not hear a response. Let me try again.</Say>
    <Redirect method="POST">{ngrok_url}/api/appointments/call-retry/{appointment.id}/</Redirect>
</Response>'''
    
    print("\n" + "=" * 60)
    print("INSTRUCTIONS:")
    print("=" * 60)
    print("1. You will receive a call shortly")
    print("2. The AI will introduce itself as calling for Rahul Sharma")
    print("3. YOU play the hospital receptionist")
    print("4. Have a natural conversation to book an appointment")
    print("5. Example responses:")
    print("   - 'Hello, City General Hospital, how can I help?'")
    print("   - 'What symptoms is the patient experiencing?'")
    print("   - 'We have Dr. Kumar available tomorrow at 10 AM'")
    print("   - 'Your appointment is confirmed for tomorrow 10 AM'")
    print("=" * 60)
    
    # Make the call
    print("\nInitiating call...")
    
    call = client.calls.create(
        twiml=twiml,
        to=to_number,
        from_=from_number,
        status_callback=status_url,
        status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
        status_callback_method='POST'
    )
    
    appointment.call_sid = call.sid
    appointment.save()
    
    print(f"\nCall initiated!")
    print(f"Call SID: {call.sid}")
    print(f"Appointment ID: {appointment.id}")
    print(f"\nAnswer the call now!")
    
    return appointment.id


if __name__ == '__main__':
    apt_id = make_full_ai_call()
    if apt_id:
        print(f"\n\nTo check appointment status later, run:")
        print(f"  python -c \"import django; django.setup(); from api.models import Appointment; a = Appointment.objects.get(id={apt_id}); print(f'Status: {{a.status}}'); print(f'Transcript: {{a.call_transcript}}')\""
        )

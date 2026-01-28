"""
Test script for REAL AI appointment booking call.
This will call your TEST_PHONE_NUMBER and use Gemini AI to have a conversation.
YOU will act as the hospital receptionist.
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings
from twilio.rest import Client
from api.appointment_service import generate_ai_response


def make_ai_appointment_call():
    """Make a real AI appointment booking call."""
    print("=" * 60)
    print("REAL AI APPOINTMENT BOOKING CALL")
    print("=" * 60)
    
    # Get credentials
    account_sid = settings.TWILIO_ACCOUNT_SID.strip("'\"")
    auth_token = settings.TWILIO_AUTH_TOKEN.strip("'\"")
    from_number = settings.TWILIO_PHONE_NUMBER.strip("'\"")
    to_number = settings.TEST_PHONE_NUMBER.strip("'\"")
    
    print(f"From: {from_number}")
    print(f"To: {to_number}")
    
    # Patient info
    patient_info = {
        'full_name': 'Rahul Sharma',
        'age': 28,
        'symptoms_current': 'Fever and severe headache for 3 days'
    }
    hospital_name = 'City General Hospital'
    purpose = 'Fever and severe headache for 3 days'
    
    print(f"\nPatient: {patient_info['full_name']}")
    print(f"Hospital: {hospital_name}")
    print(f"Purpose: {purpose}")
    
    # Generate initial AI message
    print("\nGenerating AI opening message...")
    initial_message = generate_ai_response(
        hospital_name=hospital_name,
        patient_info=patient_info,
        purpose=purpose,
        conversation_history=[],
        is_initial=True
    )
    print(f"AI will say: {initial_message}")
    
    # Create Twilio client
    client = Client(account_sid, auth_token)
    
    # Create TwiML for interactive call
    # The AI speaks, then gathers your speech response
    twiml = f'''
    <Response>
        <Say voice="Polly.Aditi" language="en-IN">
            {initial_message}
        </Say>
        <Gather input="speech" timeout="10" speechTimeout="auto" language="en-IN">
            <Say voice="Polly.Aditi">I am listening for your response.</Say>
        </Gather>
        <Say voice="Polly.Aditi">
            I did not receive a response. Thank you for your time. Goodbye.
        </Say>
    </Response>
    '''
    
    print("\n" + "=" * 60)
    print("INSTRUCTIONS:")
    print("=" * 60)
    print("1. You will receive a call shortly")
    print("2. The AI will introduce itself and request an appointment")
    print("3. YOU act as the hospital receptionist")
    print("4. Respond naturally (e.g., 'Yes, we have an opening tomorrow at 10 AM')")
    print("=" * 60)
    
    # Make the call
    print("\nInitiating call...")
    
    call = client.calls.create(
        twiml=twiml,
        to=to_number,
        from_=from_number
    )
    
    print(f"\nCall initiated!")
    print(f"Call SID: {call.sid}")
    print(f"Status: {call.status}")
    print(f"\nAnswer the call and pretend to be a hospital receptionist!")


if __name__ == '__main__':
    make_ai_appointment_call()

"""
Test script for REAL Twilio call.
This will actually call your TEST_PHONE_NUMBER.
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings
from twilio.rest import Client


def make_test_call():
    """Make a real test call using Twilio."""
    print("=" * 60)
    print("REAL TWILIO CALL TEST")
    print("=" * 60)
    
    # Get credentials
    account_sid = settings.TWILIO_ACCOUNT_SID.strip("'\"")
    auth_token = settings.TWILIO_AUTH_TOKEN.strip("'\"")
    from_number = settings.TWILIO_PHONE_NUMBER.strip("'\"")
    to_number = settings.TEST_PHONE_NUMBER.strip("'\"")
    
    print(f"From: {from_number}")
    print(f"To: {to_number}")
    
    if not all([account_sid, auth_token, from_number, to_number]):
        print("\n[ERROR] Missing Twilio configuration!")
        return
    
    # Create Twilio client
    client = Client(account_sid, auth_token)
    
    # Make a simple test call with TwiML
    print("\nInitiating call...")
    
    call = client.calls.create(
        twiml='<Response><Say voice="Polly.Aditi">Hello! This is a test call from your health appointment booking system. The AI calling feature is working correctly. Goodbye!</Say></Response>',
        to=to_number,
        from_=from_number
    )
    
    print(f"\nCall initiated!")
    print(f"Call SID: {call.sid}")
    print(f"Status: {call.status}")
    print(f"\nYou should receive a call on {to_number} shortly!")


if __name__ == '__main__':
    make_test_call()

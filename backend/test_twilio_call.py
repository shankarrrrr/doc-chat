"""
Test script for Twilio appointment booking with Gemini AI.
Run this to test the appointment booking simulation.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings
from api.models import Profile, Appointment
from api.appointment_service import simulate_appointment_booking, get_phone_number_to_call
import uuid


def test_config():
    """Test that all required settings are configured."""
    print("=" * 60)
    print("CONFIGURATION CHECK")
    print("=" * 60)
    
    gemini_key = settings.GEMINI_API_KEY
    twilio_sid = settings.TWILIO_ACCOUNT_SID
    twilio_token = settings.TWILIO_AUTH_TOKEN
    twilio_phone = settings.TWILIO_PHONE_NUMBER
    test_phone = settings.TEST_PHONE_NUMBER
    
    print(f"GEMINI_API_KEY: {'[SET]' if gemini_key and gemini_key != 'your_gemini_api_key_here' else '[NOT SET]'}")
    print(f"TWILIO_ACCOUNT_SID: {'[SET]' if twilio_sid else '[NOT SET]'}")
    print(f"TWILIO_AUTH_TOKEN: {'[SET]' if twilio_token else '[NOT SET]'}")
    print(f"TWILIO_PHONE_NUMBER: {twilio_phone if twilio_phone else '[NOT SET]'}")
    print(f"TEST_PHONE_NUMBER: {test_phone if test_phone else '[NOT SET]'}")
    
    # Test phone number routing
    print(f"\nPhone number to call (for hospital +1234567890): {get_phone_number_to_call('+1234567890')}")
    
    return gemini_key and gemini_key != 'your_gemini_api_key_here'


def test_simulation():
    """Test the appointment booking simulation."""
    print("\n" + "=" * 60)
    print("APPOINTMENT BOOKING SIMULATION TEST")
    print("=" * 60)
    
    # Create or get test profile
    test_uid = uuid.uuid4()
    profile, created = Profile.objects.get_or_create(
        email='twilio_test@example.com',
        defaults={
            'supabase_uid': test_uid,
            'full_name': 'Test Patient',
            'onboarding_completed': True,
            'onboarding_data': {
                'full_name': 'Test Patient',
                'age': 30,
                'symptoms_current': 'Fever and headache for 2 days'
            }
        }
    )
    
    if created:
        print(f"Created test profile: {profile.email}")
    else:
        print(f"Using existing profile: {profile.email}")
    
    # Create appointment
    appointment = Appointment.objects.create(
        profile=profile,
        hospital_name='City General Hospital',
        hospital_phone='+919876543210',
        hospital_address='123 Medical Street, Mumbai',
        purpose='Fever and headache - need consultation'
    )
    print(f"\nCreated appointment ID: {appointment.id}")
    print(f"Hospital: {appointment.hospital_name}")
    print(f"Purpose: {appointment.purpose}")
    print(f"Status: {appointment.status}")
    
    # Run simulation
    print("\n--- Starting AI Simulation ---\n")
    
    patient_info = profile.onboarding_data or {}
    patient_info['full_name'] = profile.full_name
    
    result = simulate_appointment_booking(appointment.id, patient_info)
    
    print("\n--- Simulation Result ---")
    print(f"Success: {result.get('success')}")
    print(f"Status: {result.get('status')}")
    
    if result.get('success'):
        print(f"Appointment Date: {result.get('appointment_date')}")
        print(f"Appointment Time: {result.get('appointment_time')}")
        print(f"Doctor: {result.get('doctor_name')}")
        print(f"Department: {result.get('department')}")
        
        print("\n--- Call Transcript ---")
        print(result.get('transcript', 'No transcript available'))
    else:
        print(f"Error: {result.get('error')}")
    
    # Refresh and show final appointment state
    appointment.refresh_from_db()
    print("\n--- Final Appointment State ---")
    print(f"Status: {appointment.status}")
    print(f"Date: {appointment.appointment_date}")
    print(f"Time: {appointment.appointment_time}")
    print(f"Doctor: {appointment.doctor_name}")
    print(f"Department: {appointment.department}")
    print(f"Notes: {appointment.notes}")
    
    return result.get('success')


def cleanup():
    """Clean up test data."""
    print("\n--- Cleanup ---")
    deleted_appointments = Appointment.objects.filter(
        profile__email='twilio_test@example.com'
    ).delete()
    print(f"Deleted {deleted_appointments[0]} test appointments")


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("TWILIO + GEMINI APPOINTMENT BOOKING TEST")
    print("=" * 60 + "\n")
    
    # Check config
    config_ok = test_config()
    
    if not config_ok:
        print("\n[ERROR] Gemini API key not configured. Cannot run simulation.")
        print("Please set GEMINI_API_KEY in your .env file.")
        sys.exit(1)
    
    try:
        # Run simulation test
        success = test_simulation()
        
        if success:
            print("\n" + "=" * 60)
            print("[SUCCESS] Appointment booking simulation completed!")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("[FAILED] Appointment booking simulation failed.")
            print("=" * 60)
            
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        cleanup()

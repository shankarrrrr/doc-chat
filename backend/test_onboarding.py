"""
Test script to verify onboarding data flow
Run with: .venv\Scripts\python.exe backend/test_onboarding.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Profile

print("\n=== Current Profiles in Database ===\n")
profiles = Profile.objects.all()
print(f"Total profiles: {profiles.count()}\n")

for p in profiles:
    print(f"Email: {p.email}")
    print(f"  Name: {p.full_name}")
    print(f"  Completed: {p.onboarding_completed}")
    print(f"  Data keys: {list(p.onboarding_data.keys())}")
    if p.onboarding_data:
        print(f"  Data: {p.onboarding_data}")
    print()

print("\n=== Testing Data Validation ===\n")

# Check which profiles should NOT show as completed (according to our frontend logic)
for p in profiles:
    data = p.onboarding_data or {}
    has_data = len(data.keys()) > 0
    completed = p.onboarding_completed and has_data
    
    status = "[OK]" if completed else "[SHOULD SHOW QUESTIONNAIRE]"
    print(f"{p.email}: {status}")
    print(f"  onboarding_completed={p.onboarding_completed}, has_data={has_data}, data_keys_count={len(data.keys())}")
    print()

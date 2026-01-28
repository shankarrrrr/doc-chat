"""
Tests for the Appointment Booking System.
"""

import json
import uuid
from datetime import date, time, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.conf import settings

from .models import Profile, Appointment


class AppointmentModelTestCase(TestCase):
    """Tests for the Appointment model."""

    def setUp(self):
        self.profile = Profile.objects.create(
            supabase_uid=uuid.uuid4(),
            email='patient@test.com',
            full_name='Test Patient',
            onboarding_completed=True,
            onboarding_data={'full_name': 'Test Patient', 'age': 30}
        )

    def test_create_appointment(self):
        """Test creating a basic appointment."""
        apt = Appointment.objects.create(
            profile=self.profile,
            hospital_name='Test Hospital',
            purpose='General checkup'
        )
        self.assertEqual(apt.hospital_name, 'Test Hospital')
        self.assertEqual(apt.status, 'pending')

    def test_appointment_status_choices(self):
        """Test all valid status choices."""
        for status in ['pending', 'calling', 'confirmed', 'failed', 'cancelled']:
            apt = Appointment.objects.create(
                profile=self.profile,
                hospital_name=f'Hospital {status}',
                status=status
            )
            self.assertEqual(apt.status, status)

    def test_confirmed_appointment_with_details(self):
        """Test a confirmed appointment with full details."""
        apt = Appointment.objects.create(
            profile=self.profile,
            hospital_name='City Hospital',
            appointment_date=date.today() + timedelta(days=3),
            appointment_time=time(10, 30),
            doctor_name='Dr. Smith',
            department='General Medicine',
            status='confirmed'
        )
        self.assertEqual(apt.status, 'confirmed')
        self.assertEqual(apt.doctor_name, 'Dr. Smith')

    def test_cascade_delete(self):
        """Test that appointments are deleted when profile is deleted."""
        Appointment.objects.create(profile=self.profile, hospital_name='H1')
        Appointment.objects.create(profile=self.profile, hospital_name='H2')
        self.assertEqual(Appointment.objects.count(), 2)
        self.profile.delete()
        self.assertEqual(Appointment.objects.count(), 0)


class AppointmentAPITestCase(TestCase):
    """Tests for appointment API endpoints."""

    def setUp(self):
        self.client = Client()
        self.user_uid = uuid.uuid4()
        self.profile = Profile.objects.create(
            supabase_uid=self.user_uid,
            email='api_test@example.com',
            full_name='API Test User',
            onboarding_completed=True,
            onboarding_data={'full_name': 'API Test User', 'age': 35}
        )
        self.mock_user = MagicMock()
        self.mock_user.id = str(self.user_uid)
        self.mock_user.email = 'api_test@example.com'

    @patch('api.decorators.get_supabase_user')
    def test_get_appointments_empty(self, mock_auth):
        """Test getting appointments when none exist."""
        mock_auth.return_value = self.mock_user
        response = self.client.get('/api/appointments/', HTTP_AUTHORIZATION='Bearer test')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['appointments'], [])

    @patch('api.decorators.get_supabase_user')
    def test_get_appointments_with_data(self, mock_auth):
        """Test getting appointments with existing data."""
        mock_auth.return_value = self.mock_user
        Appointment.objects.create(
            profile=self.profile,
            hospital_name='Test Hospital',
            status='confirmed'
        )
        response = self.client.get('/api/appointments/', HTTP_AUTHORIZATION='Bearer test')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['appointments']), 1)

    @patch('api.appointment_service.simulate_appointment_booking')
    @patch('api.decorators.get_supabase_user')
    def test_create_appointment(self, mock_auth, mock_simulate):
        """Test creating a new appointment."""
        mock_auth.return_value = self.mock_user
        mock_simulate.return_value = {'success': True, 'status': 'confirmed'}
        
        response = self.client.post(
            '/api/appointments/',
            data=json.dumps({'hospital_name': 'New Hospital', 'purpose': 'Checkup'}),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer test'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

    @patch('api.decorators.get_supabase_user')
    def test_create_appointment_missing_name(self, mock_auth):
        """Test creating appointment without hospital name fails."""
        mock_auth.return_value = self.mock_user
        response = self.client.post(
            '/api/appointments/',
            data=json.dumps({'purpose': 'Checkup'}),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer test'
        )
        self.assertEqual(response.status_code, 400)

    @patch('api.decorators.get_supabase_user')
    def test_cancel_appointment(self, mock_auth):
        """Test cancelling an appointment."""
        mock_auth.return_value = self.mock_user
        apt = Appointment.objects.create(
            profile=self.profile,
            hospital_name='Cancel Hospital',
            status='confirmed'
        )
        response = self.client.post(
            f'/api/appointments/{apt.id}/cancel/',
            HTTP_AUTHORIZATION='Bearer test'
        )
        self.assertEqual(response.status_code, 200)
        apt.refresh_from_db()
        self.assertEqual(apt.status, 'cancelled')

    @patch('api.decorators.get_supabase_user')
    def test_appointments_isolation(self, mock_auth):
        """Test that users can only see their own appointments."""
        mock_auth.return_value = self.mock_user
        other_profile = Profile.objects.create(supabase_uid=uuid.uuid4(), email='other@test.com')
        Appointment.objects.create(profile=other_profile, hospital_name='Other Hospital')
        Appointment.objects.create(profile=self.profile, hospital_name='My Hospital')
        
        response = self.client.get('/api/appointments/', HTTP_AUTHORIZATION='Bearer test')
        self.assertEqual(len(response.json()['appointments']), 1)
        self.assertEqual(response.json()['appointments'][0]['hospital_name'], 'My Hospital')


class TestPhoneNumberConfigTestCase(TestCase):
    """Tests to verify TEST_PHONE_NUMBER is always used."""

    def test_test_phone_number_configured(self):
        """Verify TEST_PHONE_NUMBER is set in settings."""
        test_number = getattr(settings, 'TEST_PHONE_NUMBER', None)
        self.assertIsNotNone(test_number)
        self.assertTrue(len(test_number.strip("'\"")) > 0)

    def test_get_phone_always_returns_test_number(self):
        """Test that get_phone_number_to_call always returns TEST_PHONE_NUMBER."""
        from .appointment_service import get_phone_number_to_call
        
        test_number = settings.TEST_PHONE_NUMBER.strip("'\"")
        
        # Test with various hospital numbers - should always return test number
        for hospital_num in ['+911234567890', '+919876543210', '+14155551234']:
            result = get_phone_number_to_call(hospital_num)
            self.assertEqual(result, test_number)


class AppointmentServiceTestCase(TestCase):
    """Tests for appointment service functions."""

    def setUp(self):
        self.profile = Profile.objects.create(
            supabase_uid=uuid.uuid4(),
            email='service@test.com',
            full_name='Service Test',
            onboarding_data={'full_name': 'Service Test', 'symptoms_current': 'Headache'}
        )

    @patch('api.appointment_service.genai')
    def test_simulate_appointment_booking(self, mock_genai):
        """Test simulated appointment booking."""
        from .appointment_service import simulate_appointment_booking
        
        mock_model = MagicMock()
        
        # First call - conversation simulation
        conv_resp = MagicMock()
        conv_resp.text = "AI: Hello\nReceptionist: Hi, confirmed for tomorrow 10AM with Dr. Test"
        
        # Second call - extract details
        details_resp = MagicMock()
        details_resp.text = json.dumps({
            'appointment_confirmed': True,
            'appointment_date': '2025-01-15',
            'appointment_time': '10:00',
            'doctor_name': 'Dr. Test',
            'department': 'General'
        })
        
        mock_model.generate_content.side_effect = [conv_resp, details_resp]
        mock_genai.GenerativeModel.return_value = mock_model
        
        apt = Appointment.objects.create(
            profile=self.profile,
            hospital_name='Test Hospital',
            purpose='Headache'
        )
        
        result = simulate_appointment_booking(apt.id, {'full_name': 'Service Test'})
        
        self.assertTrue(result['success'])
        apt.refresh_from_db()
        self.assertEqual(apt.status, 'confirmed')


class IntegrationTestCase(TestCase):
    """Integration tests for the complete booking flow."""

    def setUp(self):
        self.client = Client()
        self.user_uid = uuid.uuid4()
        self.profile = Profile.objects.create(
            supabase_uid=self.user_uid,
            email='integration@test.com',
            full_name='Integration User',
            onboarding_completed=True,
            onboarding_data={'full_name': 'Integration User', 'symptoms_current': 'Fever'}
        )
        self.mock_user = MagicMock()
        self.mock_user.id = str(self.user_uid)
        self.mock_user.email = 'integration@test.com'

    @patch('api.appointment_service.genai')
    @patch('api.decorators.get_supabase_user')
    def test_full_booking_flow(self, mock_auth, mock_genai):
        """Test complete appointment booking flow."""
        mock_auth.return_value = self.mock_user
        
        mock_model = MagicMock()
        
        # First call - conversation simulation
        conv_resp = MagicMock()
        conv_resp.text = "AI: Booking for fever\nReceptionist: Confirmed tomorrow 2PM Dr. Kumar"
        
        # Second call - extract details
        details_resp = MagicMock()
        details_resp.text = json.dumps({
            'appointment_confirmed': True,
            'appointment_date': (date.today() + timedelta(days=1)).strftime('%Y-%m-%d'),
            'appointment_time': '14:00',
            'doctor_name': 'Dr. Kumar',
            'department': 'General Medicine'
        })
        
        mock_model.generate_content.side_effect = [conv_resp, details_resp]
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Create appointment
        response = self.client.post(
            '/api/appointments/',
            data=json.dumps({
                'hospital_name': 'Apollo Hospital',
                'purpose': 'Fever'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer test'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['appointment']['status'], 'confirmed')
        self.assertEqual(data['appointment']['doctor_name'], 'Dr. Kumar')

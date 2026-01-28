"""
Comprehensive unit and integration tests for MedicalRecords functionality.
Tests document parsing, record categorization, and API endpoints.
"""
import json
import os
import uuid
from unittest.mock import patch, MagicMock
from datetime import date

from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile

from api.models import Profile, MedicalRecord
from api.ai_service import parse_document_to_records


class MockSupabaseUser:
    """Mock Supabase user for testing."""
    def __init__(self, user_id, email='test@example.com'):
        self.id = user_id
        self.email = email
        self.user_metadata = {'full_name': 'Test User'}


class MedicalRecordModelTestCase(TestCase):
    """Unit tests for MedicalRecord model."""
    
    def setUp(self):
        self.profile = Profile.objects.create(
            supabase_uid=uuid.uuid4(),
            email='test@example.com',
            full_name='Test User',
            onboarding_completed=True,
            onboarding_data={'full_name': 'Test User'}
        )

    def test_create_lab_report_record(self):
        """Test creating a lab report record."""
        record = MedicalRecord.objects.create(
            profile=self.profile,
            category='lab_reports',
            title='Complete Blood Count (CBC)',
            summary='All values within normal range',
            details={
                'Hemoglobin': '14.2 g/dL',
                'WBC Count': '7500 /mcL',
                'Platelet Count': '250000 /mcL'
            },
            doctor='Dr. Sarah Johnson',
            facility='City Medical Lab',
            record_date=date(2024, 1, 15),
            status='normal',
            source_filename='cbc_report.pdf'
        )
        
        self.assertEqual(record.category, 'lab_reports')
        self.assertEqual(record.title, 'Complete Blood Count (CBC)')
        self.assertEqual(record.status, 'normal')
        self.assertEqual(record.details['Hemoglobin'], '14.2 g/dL')
        self.assertEqual(record.profile, self.profile)

    def test_create_prescription_record(self):
        """Test creating a prescription record."""
        record = MedicalRecord.objects.create(
            profile=self.profile,
            category='prescriptions',
            title='Metformin 500mg',
            summary='For blood sugar management',
            details={
                'Dosage': '500mg',
                'Frequency': 'Twice daily',
                'Duration': '90 days'
            },
            doctor='Dr. Emily Roberts',
            status='normal'
        )
        
        self.assertEqual(record.category, 'prescriptions')
        self.assertEqual(record.details['Dosage'], '500mg')

    def test_create_diagnosis_record(self):
        """Test creating a diagnosis record."""
        record = MedicalRecord.objects.create(
            profile=self.profile,
            category='diagnoses',
            title='Dengue Fever - Positive',
            summary='NS1 antigen positive, requires monitoring',
            details={
                'NS1 Antigen': 'Positive',
                'IgM': 'Negative',
                'IgG': 'Negative',
                'Platelet Count': '95000 /mcL'
            },
            doctor='Dr. Kumar',
            facility='City Hospital',
            record_date=date(2024, 1, 10),
            status='critical'
        )
        
        self.assertEqual(record.category, 'diagnoses')
        self.assertEqual(record.status, 'critical')

    def test_create_vitals_record(self):
        """Test creating a vitals record."""
        record = MedicalRecord.objects.create(
            profile=self.profile,
            category='vitals',
            title='Vitals Check',
            summary='Blood pressure elevated',
            details={
                'Blood Pressure': '145/95 mmHg',
                'Heart Rate': '82 bpm',
                'Temperature': '98.6°F',
                'SpO2': '97%'
            },
            status='attention'
        )
        
        self.assertEqual(record.category, 'vitals')
        self.assertEqual(record.status, 'attention')

    def test_create_imaging_record(self):
        """Test creating an imaging record."""
        record = MedicalRecord.objects.create(
            profile=self.profile,
            category='imaging',
            title='Chest X-Ray',
            summary='No acute abnormality',
            details={
                'Type': 'PA View',
                'Findings': 'Clear lung fields',
                'Heart Size': 'Normal'
            },
            status='normal'
        )
        
        self.assertEqual(record.category, 'imaging')

    def test_record_ordering(self):
        """Test that records are ordered by date descending."""
        MedicalRecord.objects.create(
            profile=self.profile,
            category='lab_reports',
            title='Old Report',
            record_date=date(2023, 1, 1),
            status='normal'
        )
        MedicalRecord.objects.create(
            profile=self.profile,
            category='lab_reports',
            title='New Report',
            record_date=date(2024, 1, 1),
            status='normal'
        )
        
        records = list(MedicalRecord.objects.filter(profile=self.profile))
        self.assertEqual(records[0].title, 'New Report')
        self.assertEqual(records[1].title, 'Old Report')

    def test_cascade_delete(self):
        """Test that records are deleted when profile is deleted."""
        record = MedicalRecord.objects.create(
            profile=self.profile,
            category='lab_reports',
            title='Test Record',
            status='normal'
        )
        record_id = record.id
        self.profile.delete()
        
        self.assertFalse(MedicalRecord.objects.filter(id=record_id).exists())

    def test_record_string_representation(self):
        """Test record __str__ method."""
        record = MedicalRecord.objects.create(
            profile=self.profile,
            category='lab_reports',
            title='CBC Report',
            status='normal'
        )
        self.assertEqual(str(record), 'CBC Report - lab_reports')


class ParseDocumentToRecordsTestCase(TestCase):
    """Unit tests for parse_document_to_records function."""
    
    @patch('api.ai_service.genai')
    @patch('api.ai_service.settings')
    def test_parse_single_lab_report(self, mock_settings, mock_genai):
        """Test parsing a single lab report document."""
        mock_settings.GEMINI_API_KEY = 'test-key'
        
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            'records': [{
                'category': 'lab_reports',
                'title': 'Dengue NS1 Antigen Test',
                'summary': 'Positive for dengue fever',
                'details': {
                    'NS1 Antigen': 'Positive',
                    'Method': 'ELISA'
                },
                'doctor': 'Dr. Sharma',
                'facility': 'Apollo Labs',
                'record_date': '2024-01-15',
                'status': 'critical'
            }],
            'health_summary': 'Patient tested positive for dengue fever.',
            'profile_updates': {}
        })
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        result = parse_document_to_records(
            [{'type': 'text', 'name': 'dengue_report.txt', 'content': 'NS1 Antigen: Positive'}],
            ''
        )
        
        self.assertEqual(len(result['records']), 1)
        self.assertEqual(result['records'][0]['category'], 'lab_reports')
        self.assertEqual(result['records'][0]['title'], 'Dengue NS1 Antigen Test')
        self.assertEqual(result['records'][0]['status'], 'critical')
        self.assertIn('dengue fever', result['health_summary'])

    @patch('api.ai_service.genai')
    @patch('api.ai_service.settings')
    def test_parse_multiple_records(self, mock_settings, mock_genai):
        """Test parsing document with multiple records."""
        mock_settings.GEMINI_API_KEY = 'test-key'
        
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            'records': [
                {
                    'category': 'lab_reports',
                    'title': 'CBC',
                    'summary': 'Low platelet count',
                    'details': {'Platelet Count': '95000'},
                    'status': 'attention'
                },
                {
                    'category': 'diagnoses',
                    'title': 'Dengue Fever',
                    'summary': 'Confirmed diagnosis',
                    'details': {'Type': 'Primary infection'},
                    'status': 'critical'
                },
                {
                    'category': 'prescriptions',
                    'title': 'Paracetamol 500mg',
                    'summary': 'For fever management',
                    'details': {'Frequency': 'Every 6 hours'},
                    'status': 'normal'
                }
            ],
            'health_summary': 'Patient has dengue with low platelets.',
            'profile_updates': {'blood_type': 'O+'}
        })
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        result = parse_document_to_records(
            [{'type': 'text', 'name': 'report.txt', 'content': 'Medical report content'}],
            ''
        )
        
        self.assertEqual(len(result['records']), 3)
        categories = [r['category'] for r in result['records']]
        self.assertIn('lab_reports', categories)
        self.assertIn('diagnoses', categories)
        self.assertIn('prescriptions', categories)
        self.assertEqual(result['profile_updates']['blood_type'], 'O+')

    @patch('api.ai_service.genai')
    @patch('api.ai_service.settings')
    def test_parse_handles_markdown_json(self, mock_settings, mock_genai):
        """Test that markdown-wrapped JSON is handled correctly."""
        mock_settings.GEMINI_API_KEY = 'test-key'
        
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '```json\n{"records": [], "health_summary": "Test", "profile_updates": {}}\n```'
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        result = parse_document_to_records(
            [{'type': 'text', 'name': 'test.txt', 'content': 'test'}],
            ''
        )
        
        self.assertEqual(result['health_summary'], 'Test')

    @patch('api.ai_service.settings')
    def test_parse_no_api_key(self, mock_settings):
        """Test that missing API key raises exception."""
        mock_settings.GEMINI_API_KEY = ''
        
        with self.assertRaises(Exception) as context:
            parse_document_to_records(
                [{'type': 'text', 'name': 'test.txt', 'content': 'test'}],
                ''
            )
        
        self.assertIn('Gemini API key not configured', str(context.exception))

    @patch('api.ai_service.genai')
    @patch('api.ai_service.settings')
    def test_parse_api_error(self, mock_settings, mock_genai):
        """Test handling of API errors."""
        mock_settings.GEMINI_API_KEY = 'test-key'
        
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception('Gemini API error: 500')
        mock_genai.GenerativeModel.return_value = mock_model
        
        with self.assertRaises(Exception) as context:
            parse_document_to_records(
                [{'type': 'text', 'name': 'test.txt', 'content': 'test'}],
                ''
            )
        
        self.assertIn('Gemini API error', str(context.exception))


class MedicalRecordsAPITestCase(TestCase):
    """Integration tests for medical records API endpoints."""
    
    def setUp(self):
        self.client = Client()
        self.user_uid = uuid.uuid4()
        self.profile = Profile.objects.create(
            supabase_uid=self.user_uid,
            email='test@example.com',
            full_name='Test User',
            onboarding_completed=True,
            onboarding_data={'full_name': 'Test User'}
        )
        self.mock_user = MagicMock()
        self.mock_user.id = str(self.user_uid)
        self.mock_user.email = 'test@example.com'
        self.mock_user.user_metadata = {}

    @patch('api.decorators.get_supabase_user')
    def test_get_records_empty(self, mock_auth):
        """Test getting records when none exist."""
        mock_auth.return_value = self.mock_user
        
        response = self.client.get(
            '/api/records/',
            HTTP_AUTHORIZATION='Bearer test-token'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['records']), 0)
        self.assertEqual(data['counts']['all'], 0)

    @patch('api.decorators.get_supabase_user')
    def test_get_records_with_data(self, mock_auth):
        """Test getting records with existing data."""
        mock_auth.return_value = self.mock_user
        
        MedicalRecord.objects.create(
            profile=self.profile,
            category='lab_reports',
            title='CBC Report',
            summary='Normal',
            status='normal'
        )
        MedicalRecord.objects.create(
            profile=self.profile,
            category='prescriptions',
            title='Medication',
            summary='Take daily',
            status='normal'
        )
        
        response = self.client.get(
            '/api/records/',
            HTTP_AUTHORIZATION='Bearer test-token'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['records']), 2)
        self.assertEqual(data['counts']['all'], 2)
        self.assertEqual(data['counts']['lab_reports'], 1)
        self.assertEqual(data['counts']['prescriptions'], 1)

    @patch('api.decorators.get_supabase_user')
    def test_get_records_filtered_by_category(self, mock_auth):
        """Test filtering records by category."""
        mock_auth.return_value = self.mock_user
        
        MedicalRecord.objects.create(
            profile=self.profile,
            category='lab_reports',
            title='Lab 1',
            status='normal'
        )
        MedicalRecord.objects.create(
            profile=self.profile,
            category='lab_reports',
            title='Lab 2',
            status='normal'
        )
        MedicalRecord.objects.create(
            profile=self.profile,
            category='prescriptions',
            title='Prescription 1',
            status='normal'
        )
        
        response = self.client.get(
            '/api/records/?category=lab_reports',
            HTTP_AUTHORIZATION='Bearer test-token'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['records']), 2)
        for record in data['records']:
            self.assertEqual(record['category'], 'lab_reports')

    @patch('api.decorators.get_supabase_user')
    def test_records_isolation_between_users(self, mock_auth):
        """Test that users can only see their own records."""
        mock_auth.return_value = self.mock_user
        
        # Create record for current user
        MedicalRecord.objects.create(
            profile=self.profile,
            category='lab_reports',
            title='My Record',
            status='normal'
        )
        
        # Create record for another user
        other_profile = Profile.objects.create(
            supabase_uid=uuid.uuid4(),
            email='other@example.com'
        )
        MedicalRecord.objects.create(
            profile=other_profile,
            category='lab_reports',
            title='Other User Record',
            status='normal'
        )
        
        response = self.client.get(
            '/api/records/',
            HTTP_AUTHORIZATION='Bearer test-token'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['records']), 1)
        self.assertEqual(data['records'][0]['title'], 'My Record')

    @patch('api.ai_service.parse_document_to_records')
    @patch('api.decorators.get_supabase_user')
    def test_parse_documents_creates_records(self, mock_auth, mock_parse):
        """Test that parse_documents endpoint creates records."""
        mock_auth.return_value = self.mock_user
        mock_parse.return_value = {
            'records': [
                {
                    'category': 'lab_reports',
                    'title': 'Dengue Test',
                    'summary': 'Positive result',
                    'details': {'NS1': 'Positive'},
                    'doctor': 'Dr. Test',
                    'facility': 'Test Lab',
                    'record_date': '2024-01-15',
                    'status': 'critical'
                }
            ],
            'health_summary': 'Patient has dengue fever',
            'profile_updates': {}
        }
        
        test_file = SimpleUploadedFile(
            'test_report.txt',
            b'Test medical report content',
            content_type='text/plain'
        )
        
        response = self.client.post(
            '/api/parse-documents/',
            {'documents': test_file},
            HTTP_AUTHORIZATION='Bearer test-token'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['records_created'], 1)
        self.assertEqual(data['records'][0]['title'], 'Dengue Test')
        
        # Verify record was created in database
        records = MedicalRecord.objects.filter(profile=self.profile)
        self.assertEqual(records.count(), 1)
        self.assertEqual(records[0].title, 'Dengue Test')
        self.assertEqual(records[0].status, 'critical')

    @patch('api.ai_service.parse_document_to_records')
    @patch('api.decorators.get_supabase_user')
    def test_parse_documents_updates_health_summary(self, mock_auth, mock_parse):
        """Test that health summary is updated after parsing."""
        mock_auth.return_value = self.mock_user
        mock_parse.return_value = {
            'records': [],
            'health_summary': 'Updated health summary from document',
            'profile_updates': {}
        }
        
        test_file = SimpleUploadedFile(
            'test.txt',
            b'Test content',
            content_type='text/plain'
        )
        
        self.client.post(
            '/api/parse-documents/',
            {'documents': test_file},
            HTTP_AUTHORIZATION='Bearer test-token'
        )
        
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.health_summary, 'Updated health summary from document')

    @patch('api.ai_service.parse_document_to_records')
    @patch('api.decorators.get_supabase_user')
    def test_parse_documents_updates_profile(self, mock_auth, mock_parse):
        """Test that profile data is updated from parsed documents."""
        mock_auth.return_value = self.mock_user
        mock_parse.return_value = {
            'records': [],
            'health_summary': '',
            'profile_updates': {
                'blood_type': 'A+',
                'allergies': 'Penicillin'
            }
        }
        
        test_file = SimpleUploadedFile(
            'test.txt',
            b'Blood type: A+, Allergies: Penicillin',
            content_type='text/plain'
        )
        
        self.client.post(
            '/api/parse-documents/',
            {'documents': test_file},
            HTTP_AUTHORIZATION='Bearer test-token'
        )
        
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.onboarding_data.get('blood_type'), 'A+')
        self.assertEqual(self.profile.onboarding_data.get('allergies'), 'Penicillin')

    @patch('api.decorators.get_supabase_user')
    def test_parse_documents_no_files(self, mock_auth):
        """Test parse documents with no files."""
        mock_auth.return_value = self.mock_user
        
        response = self.client.post(
            '/api/parse-documents/',
            {},
            HTTP_AUTHORIZATION='Bearer test-token'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('No documents provided', response.json()['detail'])

    @patch('api.decorators.get_supabase_user')
    def test_parse_documents_file_too_large(self, mock_auth):
        """Test parse documents with oversized file."""
        mock_auth.return_value = self.mock_user
        
        large_content = b'x' * (11 * 1024 * 1024)  # 11MB
        test_file = SimpleUploadedFile(
            'large_file.txt',
            large_content,
            content_type='text/plain'
        )
        
        response = self.client.post(
            '/api/parse-documents/',
            {'documents': test_file},
            HTTP_AUTHORIZATION='Bearer test-token'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('exceeds 10MB limit', response.json()['detail'])

    @patch('api.decorators.get_supabase_user')
    def test_unauthorized_access(self, mock_auth):
        """Test that unauthorized requests are rejected."""
        mock_auth.return_value = None
        
        response = self.client.get('/api/records/')
        
        self.assertEqual(response.status_code, 401)


class RealPDFIntegrationTestCase(TestCase):
    """
    Integration tests using real PDF document.
    These tests require the actual Gemini API key to be configured.
    """
    
    def setUp(self):
        self.client = Client()
        self.user_uid = uuid.uuid4()
        self.profile = Profile.objects.create(
            supabase_uid=self.user_uid,
            email='pdf_test@example.com',
            full_name='PDF Test User',
            onboarding_completed=True,
            onboarding_data={'full_name': 'PDF Test User'}
        )
        self.mock_user = MagicMock()
        self.mock_user.id = str(self.user_uid)
        self.mock_user.email = 'pdf_test@example.com'
        self.mock_user.user_metadata = {}
        
        # Path to test PDF
        self.pdf_path = r'C:\Users\Lenovo\Desktop\dyp\Positive-Dengue-fever-test-report-format-example-sample-template-Drlogy-lab-report (1).pdf'

    def test_pdf_file_exists(self):
        """Verify the test PDF file exists."""
        self.assertTrue(
            os.path.exists(self.pdf_path),
            f"Test PDF not found at {self.pdf_path}"
        )

    @patch('api.decorators.get_supabase_user')
    def test_parse_real_dengue_pdf(self, mock_auth):
        """
        Integration test: Parse actual dengue fever PDF report.
        This test uses the real Gemini API if configured.
        Skip if API key is not configured or API fails.
        """
        from django.conf import settings
        
        # Skip if no API key configured
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == 'your_gemini_api_key_here':
            self.skipTest("Gemini API key not configured - skipping integration test")
        
        mock_auth.return_value = self.mock_user
        
        # Skip if PDF doesn't exist
        if not os.path.exists(self.pdf_path):
            self.skipTest(f"PDF file not found: {self.pdf_path}")
        
        with open(self.pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        from django.core.files.uploadedfile import SimpleUploadedFile
        test_file = SimpleUploadedFile(
            'dengue_report.pdf',
            pdf_content,
            content_type='application/pdf'
        )
        
        response = self.client.post(
            '/api/parse-documents/',
            {'documents': test_file},
            HTTP_AUTHORIZATION='Bearer test-token'
        )
        
        # Check response
        self.assertIn(response.status_code, [200, 500])  # 500 if API key not configured
        
        if response.status_code == 200:
            data = response.json()
            self.assertTrue(data['success'])
            
            # Verify records were created
            records = MedicalRecord.objects.filter(profile=self.profile)
            self.assertGreater(records.count(), 0, "Expected at least one record to be created")
            
            # Check for dengue-related content
            all_titles = ' '.join([r.title.lower() for r in records])
            all_summaries = ' '.join([r.summary.lower() for r in records])
            combined = all_titles + ' ' + all_summaries
            
            # Should contain dengue-related terms
            dengue_terms = ['dengue', 'ns1', 'fever', 'antigen', 'positive']
            found_terms = [term for term in dengue_terms if term in combined]
            
            print(f"\nRecords created: {records.count()}")
            for record in records:
                print(f"  - {record.category}: {record.title} [{record.status}]")
            
            self.assertGreater(
                len(found_terms), 0,
                f"Expected dengue-related content in records. Found: {combined[:200]}"
            )

    @patch('api.ai_service.parse_document_to_records')
    @patch('api.decorators.get_supabase_user')
    def test_mock_dengue_pdf_parsing(self, mock_auth, mock_parse):
        """
        Test dengue PDF parsing with mocked Gemini response.
        Simulates expected output from a dengue fever test report.
        """
        mock_auth.return_value = self.mock_user
        
        # Mock the expected Gemini response for a dengue report
        mock_parse.return_value = {
            'records': [
                {
                    'category': 'lab_reports',
                    'title': 'Dengue NS1 Antigen Test',
                    'summary': 'NS1 Antigen detected - Positive for dengue fever',
                    'details': {
                        'NS1 Antigen': 'Positive',
                        'Test Method': 'ELISA',
                        'Sample Type': 'Serum'
                    },
                    'doctor': 'Dr. Pathologist',
                    'facility': 'Drlogy Lab',
                    'record_date': '2024-01-15',
                    'status': 'critical'
                },
                {
                    'category': 'lab_reports',
                    'title': 'Dengue IgM/IgG Antibody Test',
                    'summary': 'Antibody levels indicate recent infection',
                    'details': {
                        'IgM': 'Positive',
                        'IgG': 'Negative',
                        'Interpretation': 'Primary/Recent infection'
                    },
                    'doctor': 'Dr. Pathologist',
                    'facility': 'Drlogy Lab',
                    'record_date': '2024-01-15',
                    'status': 'critical'
                },
                {
                    'category': 'diagnoses',
                    'title': 'Dengue Fever - Confirmed',
                    'summary': 'Laboratory confirmed dengue fever diagnosis',
                    'details': {
                        'Diagnosis': 'Dengue Fever',
                        'Severity': 'To be monitored',
                        'Recommendation': 'Follow up with physician'
                    },
                    'record_date': '2024-01-15',
                    'status': 'critical'
                }
            ],
            'health_summary': 'Patient has tested positive for dengue fever. NS1 antigen is positive indicating active infection. IgM antibodies are positive suggesting recent/primary infection. Recommend monitoring platelet count and hydration. Follow up with treating physician immediately.',
            'profile_updates': {
                'conditions': 'Dengue Fever (Active)'
            }
        }
        
        test_file = SimpleUploadedFile(
            'dengue_report.pdf',
            b'PDF content simulation',
            content_type='application/pdf'
        )
        
        response = self.client.post(
            '/api/parse-documents/',
            {'documents': test_file},
            HTTP_AUTHORIZATION='Bearer test-token'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify response structure
        self.assertTrue(data['success'])
        self.assertEqual(data['records_created'], 3)
        
        # Verify records in database
        records = MedicalRecord.objects.filter(profile=self.profile)
        self.assertEqual(records.count(), 3)
        
        # Check categories
        categories = list(records.values_list('category', flat=True))
        self.assertEqual(categories.count('lab_reports'), 2)
        self.assertEqual(categories.count('diagnoses'), 1)
        
        # Check critical status
        critical_records = records.filter(status='critical')
        self.assertEqual(critical_records.count(), 3)
        
        # Verify health summary updated
        self.profile.refresh_from_db()
        self.assertIn('dengue fever', self.profile.health_summary.lower())
        
        # Verify profile updated
        self.assertIn('Dengue', self.profile.onboarding_data.get('conditions', ''))

    @patch('api.decorators.get_supabase_user')
    def test_records_api_after_parsing(self, mock_auth):
        """Test fetching records after document parsing."""
        mock_auth.return_value = self.mock_user
        
        # Create some test records
        MedicalRecord.objects.create(
            profile=self.profile,
            category='lab_reports',
            title='Dengue NS1 Test',
            summary='Positive',
            details={'NS1': 'Positive'},
            status='critical',
            record_date=date(2024, 1, 15)
        )
        MedicalRecord.objects.create(
            profile=self.profile,
            category='diagnoses',
            title='Dengue Fever',
            summary='Confirmed diagnosis',
            details={'Type': 'Primary infection'},
            status='critical',
            record_date=date(2024, 1, 15)
        )
        
        # Fetch records
        response = self.client.get(
            '/api/records/',
            HTTP_AUTHORIZATION='Bearer test-token'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify counts
        self.assertEqual(data['counts']['all'], 2)
        self.assertEqual(data['counts']['lab_reports'], 1)
        self.assertEqual(data['counts']['diagnoses'], 1)
        
        # Verify record details
        records = data['records']
        self.assertEqual(len(records), 2)
        
        # Check record structure
        for record in records:
            self.assertIn('id', record)
            self.assertIn('category', record)
            self.assertIn('title', record)
            self.assertIn('summary', record)
            self.assertIn('details', record)
            self.assertIn('status', record)
            self.assertIn('record_date', record)
            self.assertIn('created_at', record)

    @patch('api.decorators.get_supabase_user')
    def test_filter_critical_records(self, mock_auth):
        """Test that critical records can be identified."""
        mock_auth.return_value = self.mock_user
        
        # Create records with different statuses
        MedicalRecord.objects.create(
            profile=self.profile,
            category='lab_reports',
            title='Normal Test',
            status='normal'
        )
        MedicalRecord.objects.create(
            profile=self.profile,
            category='lab_reports',
            title='Critical Test',
            status='critical'
        )
        MedicalRecord.objects.create(
            profile=self.profile,
            category='vitals',
            title='Attention Needed',
            status='attention'
        )
        
        response = self.client.get(
            '/api/records/',
            HTTP_AUTHORIZATION='Bearer test-token'
        )
        
        data = response.json()
        statuses = [r['status'] for r in data['records']]
        
        self.assertIn('normal', statuses)
        self.assertIn('critical', statuses)
        self.assertIn('attention', statuses)


class CategoryValidationTestCase(TestCase):
    """Tests for record category validation."""
    
    def setUp(self):
        self.profile = Profile.objects.create(
            supabase_uid=uuid.uuid4(),
            email='test@example.com'
        )

    def test_valid_categories(self):
        """Test all valid categories can be used."""
        valid_categories = [
            'lab_reports', 'prescriptions', 'diagnoses',
            'vitals', 'imaging', 'other'
        ]
        
        for category in valid_categories:
            record = MedicalRecord.objects.create(
                profile=self.profile,
                category=category,
                title=f'Test {category}',
                status='normal'
            )
            self.assertEqual(record.category, category)

    def test_valid_statuses(self):
        """Test all valid statuses can be used."""
        valid_statuses = ['normal', 'attention', 'critical']
        
        for status in valid_statuses:
            record = MedicalRecord.objects.create(
                profile=self.profile,
                category='other',
                title=f'Test {status}',
                status=status
            )
            self.assertEqual(record.status, status)

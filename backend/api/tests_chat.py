import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from api.models import Profile, ChatSession, ChatMessage
from api.ai_service import build_patient_context, get_ai_response
import uuid


class MockSupabaseUser:
    def __init__(self, user_id, email='test@example.com'):
        self.id = user_id
        self.email = email
        self.user_metadata = {'full_name': 'Test User'}


class ChatModelsTestCase(TestCase):
    def setUp(self):
        self.profile = Profile.objects.create(
            supabase_uid=uuid.uuid4(),
            email='test@example.com',
            full_name='Test User',
            onboarding_completed=True,
            onboarding_data={
                'full_name': 'Test User',
                'age': 30,
                'sex': 'Male',
                'symptoms_current': 'Headache',
                'location': 'Mumbai'
            }
        )

    def test_chat_session_creation(self):
        session = ChatSession.objects.create(
            profile=self.profile,
            title='Test Chat'
        )
        self.assertEqual(session.profile, self.profile)
        self.assertEqual(session.title, 'Test Chat')
        self.assertIsNotNone(session.created_at)

    def test_chat_message_creation(self):
        session = ChatSession.objects.create(profile=self.profile)
        message = ChatMessage.objects.create(
            session=session,
            role='user',
            content='Hello, I have a headache'
        )
        self.assertEqual(message.session, session)
        self.assertEqual(message.role, 'user')
        self.assertEqual(message.content, 'Hello, I have a headache')

    def test_chat_session_ordering(self):
        session1 = ChatSession.objects.create(profile=self.profile, title='First')
        session2 = ChatSession.objects.create(profile=self.profile, title='Second')
        sessions = list(ChatSession.objects.filter(profile=self.profile).order_by('-updated_at'))
        self.assertEqual(len(sessions), 2)

    def test_chat_message_ordering(self):
        session = ChatSession.objects.create(profile=self.profile)
        msg1 = ChatMessage.objects.create(session=session, role='user', content='First')
        msg2 = ChatMessage.objects.create(session=session, role='ai', content='Second')
        messages = list(session.messages.all())
        self.assertEqual(messages[0].content, 'First')
        self.assertEqual(messages[1].content, 'Second')

    def test_cascade_delete(self):
        session = ChatSession.objects.create(profile=self.profile)
        ChatMessage.objects.create(session=session, role='user', content='Test')
        session_id = session.id
        session.delete()
        self.assertEqual(ChatMessage.objects.filter(session_id=session_id).count(), 0)


class AIServiceTestCase(TestCase):
    def test_build_patient_context_with_data(self):
        onboarding_data = {
            'full_name': 'John Doe',
            'age': 35,
            'sex': 'Male',
            'location': 'Delhi',
            'height': 175,
            'weight': 70,
            'symptoms_current': 'Fever',
            'medical_history': 'Diabetes'
        }
        context = build_patient_context(onboarding_data)
        self.assertIn('John Doe', context)
        self.assertIn('35', context)
        self.assertIn('Male', context)
        self.assertIn('Delhi', context)
        self.assertIn('175 cm', context)
        self.assertIn('70 kg', context)
        self.assertIn('Fever', context)
        self.assertIn('Diabetes', context)

    def test_build_patient_context_empty(self):
        context = build_patient_context({})
        self.assertEqual(context, 'No patient data available.')

    def test_build_patient_context_none(self):
        context = build_patient_context(None)
        self.assertEqual(context, 'No patient data available.')

    @patch('api.ai_service.settings')
    @patch('api.ai_service.genai')
    def test_get_ai_response_gemini_success(self, mock_genai, mock_settings):
        mock_settings.GEMINI_API_KEY = 'test_api_key'
        mock_settings.DECODO_AUTH_TOKEN = ''
        
        mock_model = MagicMock()
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = 'I recommend rest and hydration.'
        mock_chat.send_message.return_value = mock_response
        mock_model.start_chat.return_value = mock_chat
        mock_genai.GenerativeModel.return_value = mock_model
        
        messages = [{'role': 'user', 'content': 'I have a headache'}]
        response = get_ai_response(messages, {'full_name': 'Test'})
        
        self.assertEqual(response, 'I recommend rest and hydration.')
        mock_genai.configure.assert_called_once()

    @patch('api.ai_service.requests.post')
    @patch('api.ai_service.settings')
    @patch('api.ai_service.genai')
    def test_get_ai_response_fallback_to_decodo(self, mock_genai, mock_settings, mock_requests_post):
        mock_settings.GEMINI_API_KEY = 'test_api_key'
        mock_settings.DECODO_AUTH_TOKEN = 'Basic test_token'
        
        # Make Gemini fail
        mock_genai.configure.return_value = None
        mock_model = MagicMock()
        mock_model.start_chat.side_effect = Exception('Gemini error')
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Decodo fallback success
        decodo_response = MagicMock()
        decodo_response.ok = True
        decodo_response.json.return_value = {
            'results': [{'content': 'Fallback response'}]
        }
        mock_requests_post.return_value = decodo_response
        
        messages = [{'role': 'user', 'content': 'Test'}]
        response = get_ai_response(messages, {})
        
        self.assertEqual(response, 'Fallback response')

    @patch('api.ai_service.settings')
    def test_get_ai_response_no_service_configured(self, mock_settings):
        mock_settings.GEMINI_API_KEY = ''
        mock_settings.DECODO_AUTH_TOKEN = ''
        
        with self.assertRaises(Exception) as context:
            get_ai_response([{'role': 'user', 'content': 'Test'}], {})
        
        self.assertIn('AI services are unavailable', str(context.exception))


class ChatAPITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_uid = uuid.uuid4()
        self.profile = Profile.objects.create(
            supabase_uid=self.user_uid,
            email='test@example.com',
            full_name='Test User',
            onboarding_completed=True,
            onboarding_data={'full_name': 'Test User', 'age': 30}
        )

    @patch('api.decorators.get_supabase_user')
    def test_create_chat_session(self, mock_get_user):
        mock_get_user.return_value = MockSupabaseUser(str(self.user_uid))
        
        response = self.client.post(
            '/api/chat/sessions/',
            data=json.dumps({'title': 'New Chat'}),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer test_token'
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('id', data)
        self.assertEqual(data['title'], 'New Chat')

    @patch('api.decorators.get_supabase_user')
    def test_list_chat_sessions(self, mock_get_user):
        mock_get_user.return_value = MockSupabaseUser(str(self.user_uid))
        
        ChatSession.objects.create(profile=self.profile, title='Session 1')
        ChatSession.objects.create(profile=self.profile, title='Session 2')
        
        response = self.client.get(
            '/api/chat/sessions/',
            HTTP_AUTHORIZATION='Bearer test_token'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['sessions']), 2)

    @patch('api.decorators.get_supabase_user')
    def test_get_chat_session_detail(self, mock_get_user):
        mock_get_user.return_value = MockSupabaseUser(str(self.user_uid))
        
        session = ChatSession.objects.create(profile=self.profile, title='Test Session')
        ChatMessage.objects.create(session=session, role='user', content='Hello')
        ChatMessage.objects.create(session=session, role='ai', content='Hi there!')
        
        response = self.client.get(
            f'/api/chat/sessions/{session.id}/',
            HTTP_AUTHORIZATION='Bearer test_token'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['title'], 'Test Session')
        self.assertEqual(len(data['messages']), 2)

    @patch('api.decorators.get_supabase_user')
    def test_delete_chat_session(self, mock_get_user):
        mock_get_user.return_value = MockSupabaseUser(str(self.user_uid))
        
        session = ChatSession.objects.create(profile=self.profile, title='To Delete')
        
        response = self.client.delete(
            f'/api/chat/sessions/{session.id}/',
            HTTP_AUTHORIZATION='Bearer test_token'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ChatSession.objects.filter(id=session.id).exists())

    @patch('api.views.get_ai_response')
    @patch('api.decorators.get_supabase_user')
    def test_send_chat_message(self, mock_get_user, mock_ai_response):
        mock_get_user.return_value = MockSupabaseUser(str(self.user_uid))
        mock_ai_response.return_value = 'AI response here'
        
        session = ChatSession.objects.create(profile=self.profile)
        
        response = self.client.post(
            f'/api/chat/sessions/{session.id}/send/',
            data=json.dumps({'message': 'What should I do for a headache?'}),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer test_token'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['user_message']['content'], 'What should I do for a headache?')
        self.assertEqual(data['ai_message']['content'], 'AI response here')

    @patch('api.decorators.get_supabase_user')
    def test_send_empty_message(self, mock_get_user):
        mock_get_user.return_value = MockSupabaseUser(str(self.user_uid))
        
        session = ChatSession.objects.create(profile=self.profile)
        
        response = self.client.post(
            f'/api/chat/sessions/{session.id}/send/',
            data=json.dumps({'message': ''}),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer test_token'
        )
        
        self.assertEqual(response.status_code, 400)

    @patch('api.decorators.get_supabase_user')
    def test_access_other_user_session(self, mock_get_user):
        mock_get_user.return_value = MockSupabaseUser(str(self.user_uid))
        
        other_profile = Profile.objects.create(
            supabase_uid=uuid.uuid4(),
            email='other@example.com'
        )
        session = ChatSession.objects.create(profile=other_profile, title='Private')
        
        response = self.client.get(
            f'/api/chat/sessions/{session.id}/',
            HTTP_AUTHORIZATION='Bearer test_token'
        )
        
        self.assertEqual(response.status_code, 404)


class IntegrationTestCase(TestCase):
    def setUp(self):
        self.profile = Profile.objects.create(
            supabase_uid=uuid.uuid4(),
            email='integration@test.com',
            full_name='Integration Test User',
            onboarding_completed=True,
            onboarding_data={
                'full_name': 'Integration Test User',
                'age': 28,
                'sex': 'Female',
                'location': 'Bangalore',
                'symptoms_current': 'Back pain',
                'exercise_frequency': 'Rarely',
                'sleep_hours': 6,
                'stress_level': 'High'
            }
        )

    def test_full_chat_flow(self):
        session = ChatSession.objects.create(
            profile=self.profile,
            title=''
        )
        
        msg1 = ChatMessage.objects.create(
            session=session,
            role='user',
            content='I have been experiencing back pain for a week'
        )
        
        msg2 = ChatMessage.objects.create(
            session=session,
            role='ai',
            content='I see you mentioned back pain. Given your profile shows high stress and limited exercise, this could be related. Consider gentle stretching and improving sleep quality.'
        )
        
        msg3 = ChatMessage.objects.create(
            session=session,
            role='user',
            content='What exercises do you recommend?'
        )
        
        msg4 = ChatMessage.objects.create(
            session=session,
            role='ai',
            content='For back pain relief, try cat-cow stretches, child pose, and gentle walking. Start with 10-15 minutes daily.'
        )
        
        session.title = msg1.content[:50]
        session.save()
        
        messages = list(session.messages.all())
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[0].role, 'user')
        self.assertEqual(messages[1].role, 'ai')
        self.assertEqual(session.title, 'I have been experiencing back pain for a week')

    def test_multiple_sessions_per_user(self):
        session1 = ChatSession.objects.create(profile=self.profile, title='Back Pain')
        session2 = ChatSession.objects.create(profile=self.profile, title='Diet Questions')
        session3 = ChatSession.objects.create(profile=self.profile, title='Sleep Issues')
        
        ChatMessage.objects.create(session=session1, role='user', content='Back hurts')
        ChatMessage.objects.create(session=session2, role='user', content='What should I eat?')
        ChatMessage.objects.create(session=session3, role='user', content='Cannot sleep')
        
        sessions = ChatSession.objects.filter(profile=self.profile)
        self.assertEqual(sessions.count(), 3)
        
        for session in sessions:
            self.assertEqual(session.messages.count(), 1)

    def test_patient_context_in_response(self):
        context = build_patient_context(self.profile.onboarding_data)
        
        self.assertIn('Integration Test User', context)
        self.assertIn('28', context)
        self.assertIn('Female', context)
        self.assertIn('Bangalore', context)
        self.assertIn('Back pain', context)
        self.assertIn('Rarely', context)
        self.assertIn('6 hours', context)
        self.assertIn('High', context)


class DocumentParsingTestCase(TestCase):
    """Tests for document parsing functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user_uid = uuid.uuid4()
        self.profile = Profile.objects.create(
            supabase_uid=self.user_uid,
            email='doc_test@example.com',
            full_name='Doc Test User',
            onboarding_completed=True,
            onboarding_data={'full_name': 'Doc Test User'}
        )
        self.mock_user = MagicMock()
        self.mock_user.id = str(self.user_uid)
        self.mock_user.email = 'doc_test@example.com'
        self.mock_user.user_metadata = {}

    @patch('api.ai_service.parse_document_to_records')
    @patch('api.decorators.get_supabase_user')
    def test_parse_documents_success(self, mock_auth, mock_parse):
        mock_auth.return_value = self.mock_user
        mock_parse.return_value = {
            'records': [{
                'category': 'vitals',
                'title': 'Blood Pressure Reading',
                'summary': 'Normal BP',
                'details': {'BP': '120/80'},
                'status': 'normal'
            }],
            'health_summary': 'Patient vitals are normal',
            'profile_updates': {
                'blood_pressure': '120/80',
                'medications': 'Aspirin 100mg daily'
            }
        }
        
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        test_file = SimpleUploadedFile(
            'report.txt',
            b'Blood pressure: 120/80\nPrescription: Aspirin 100mg',
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

    @patch('api.decorators.get_supabase_user')
    def test_parse_documents_no_files(self, mock_auth):
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
        mock_auth.return_value = self.mock_user
        
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create a file > 10MB
        large_content = b'x' * (11 * 1024 * 1024)
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

    @patch('api.ai_service.settings')
    def test_parse_document_with_gemini_no_api_key(self, mock_settings):
        from api.ai_service import parse_document_with_gemini
        
        mock_settings.GEMINI_API_KEY = ''
        
        with self.assertRaises(Exception) as context:
            parse_document_with_gemini([{'type': 'text', 'name': 'test.txt', 'content': 'test'}], {})
        
        self.assertIn('Gemini API key not configured', str(context.exception))

    @patch('api.ai_service.genai')
    @patch('api.ai_service.settings')
    def test_parse_document_with_gemini_success(self, mock_settings, mock_genai):
        from api.ai_service import parse_document_with_gemini
        
        mock_settings.GEMINI_API_KEY = 'test-key'
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"blood_pressure": "130/85", "heart_rate": "72"}'
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        result = parse_document_with_gemini(
            [{'type': 'text', 'name': 'report.txt', 'content': 'BP: 130/85, HR: 72'}],
            {}
        )
        
        self.assertEqual(result['blood_pressure'], '130/85')
        self.assertEqual(result['heart_rate'], '72')

    @patch('api.ai_service.genai')
    @patch('api.ai_service.settings')
    def test_parse_document_handles_markdown_response(self, mock_settings, mock_genai):
        from api.ai_service import parse_document_with_gemini
        
        mock_settings.GEMINI_API_KEY = 'test-key'
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '```json\n{"allergies": "Penicillin"}\n```'
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        result = parse_document_with_gemini(
            [{'type': 'text', 'name': 'notes.txt', 'content': 'Allergic to Penicillin'}],
            {}
        )
        
        self.assertEqual(result['allergies'], 'Penicillin')

"""
Unit and Integration tests for Voice Symptom Collection Service
"""
import json
import base64
from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase, Client


class VoiceServiceUnitTests(SimpleTestCase):
    """Unit tests for voice_service.py functions"""

    def test_configure_genai_missing_key(self):
        """Test that configure_genai raises error when API key is missing"""
        from api.voice_service import configure_genai
        
        with patch('api.voice_service.settings') as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            with self.assertRaises(Exception) as context:
                configure_genai()
            self.assertIn('not configured', str(context.exception))

    @patch('api.voice_service.genai')
    @patch('api.voice_service.settings')
    def test_transcribe_audio_success(self, mock_settings, mock_genai):
        """Test successful audio transcription"""
        from api.voice_service import transcribe_audio
        
        mock_settings.GEMINI_API_KEY = 'test-key'
        
        mock_response = MagicMock()
        mock_response.text = '{"transcription": "I have a headache", "language": "en", "language_name": "English"}'
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        
        result = transcribe_audio('base64audiodatahere', 'audio/webm')
        
        self.assertEqual(result['transcription'], 'I have a headache')
        self.assertEqual(result['language'], 'en')
        self.assertEqual(result['language_name'], 'English')

    @patch('api.voice_service.genai')
    @patch('api.voice_service.settings')
    def test_transcribe_audio_hindi(self, mock_settings, mock_genai):
        """Test Hindi audio transcription"""
        from api.voice_service import transcribe_audio
        
        mock_settings.GEMINI_API_KEY = 'test-key'
        
        mock_response = MagicMock()
        mock_response.text = '{"transcription": "मुझे सिर में दर्द है", "language": "hi", "language_name": "Hindi"}'
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        
        result = transcribe_audio('base64audiodatahere', 'audio/webm')
        
        self.assertEqual(result['language'], 'hi')
        self.assertEqual(result['language_name'], 'Hindi')

    @patch('api.voice_service.genai')
    @patch('api.voice_service.settings')
    def test_transcribe_audio_invalid_json(self, mock_settings, mock_genai):
        """Test fallback when Gemini returns invalid JSON"""
        from api.voice_service import transcribe_audio
        
        mock_settings.GEMINI_API_KEY = 'test-key'
        
        mock_response = MagicMock()
        mock_response.text = 'Just plain text transcription'
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        
        result = transcribe_audio('base64audiodatahere', 'audio/webm')
        
        self.assertEqual(result['transcription'], 'Just plain text transcription')
        self.assertEqual(result['language'], 'unknown')

    @patch('api.voice_service.genai')
    @patch('api.voice_service.settings')
    def test_get_conversation_response(self, mock_settings, mock_genai):
        """Test conversation response generation"""
        from api.voice_service import get_conversation_response
        
        mock_settings.GEMINI_API_KEY = 'test-key'
        
        mock_response = MagicMock()
        mock_response.text = 'How long have you been experiencing this headache?'
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        
        result = get_conversation_response(
            'I have a headache',
            [],
            'en'
        )
        
        self.assertIn('headache', result.lower())

    @patch('api.voice_service.genai')
    @patch('api.voice_service.settings')
    def test_get_conversation_response_multilingual(self, mock_settings, mock_genai):
        """Test conversation responds in same language as user"""
        from api.voice_service import get_conversation_response
        
        mock_settings.GEMINI_API_KEY = 'test-key'
        
        mock_response = MagicMock()
        mock_response.text = 'आपको यह दर्द कब से हो रहा है?'
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        
        result = get_conversation_response(
            'मुझे सिर में दर्द है',
            [],
            'hi'
        )
        
        self.assertIsNotNone(result)

    @patch('api.voice_service.genai')
    @patch('api.voice_service.settings')
    def test_generate_symptom_summary(self, mock_settings, mock_genai):
        """Test symptom summary generation"""
        from api.voice_service import generate_symptom_summary
        
        mock_settings.GEMINI_API_KEY = 'test-key'
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            'chief_complaint': 'Severe headache for 3 days',
            'symptoms': [
                {'symptom': 'headache', 'duration': '3 days', 'severity': '7/10'}
            ],
            'summary_for_patient': 'You have reported a severe headache.',
            'summary_for_doctor': 'Patient presents with cephalgia, 3 days duration, severity 7/10.',
            'recommended_urgency': 'soon',
            'suggested_specialty': 'neurology'
        })
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        
        conversation = [
            {'role': 'user', 'content': 'I have a severe headache'},
            {'role': 'assistant', 'content': 'How long have you had this headache?'},
            {'role': 'user', 'content': '3 days'},
            {'role': 'assistant', 'content': 'On a scale of 1-10, how severe is it?'},
            {'role': 'user', 'content': 'About 7'},
        ]
        
        result = generate_symptom_summary(conversation, {'name': 'Test', 'age': 30, 'gender': 'male'})
        
        self.assertEqual(result['chief_complaint'], 'Severe headache for 3 days')
        self.assertEqual(result['recommended_urgency'], 'soon')
        self.assertEqual(len(result['symptoms']), 1)

    @patch('api.voice_service.genai')
    @patch('api.voice_service.settings')
    def test_generate_symptom_summary_invalid_json(self, mock_settings, mock_genai):
        """Test summary generation fallback on invalid JSON"""
        from api.voice_service import generate_symptom_summary
        
        mock_settings.GEMINI_API_KEY = 'test-key'
        
        mock_response = MagicMock()
        mock_response.text = 'Invalid response'
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        
        result = generate_symptom_summary(
            [{'role': 'user', 'content': 'headache'}],
            {'name': 'Test'}
        )
        
        self.assertEqual(result['chief_complaint'], 'Unable to parse symptoms')


class VoiceAPIIntegrationTests(SimpleTestCase):
    """Integration tests for voice API endpoints"""

    def setUp(self):
        self.client = Client()
        # Create mock auth token
        self.mock_token = 'mock-auth-token'

    @patch('api.decorators.get_supabase_user')
    @patch('api.voice_service.transcribe_audio')
    def test_voice_transcribe_endpoint(self, mock_transcribe, mock_auth):
        """Test /api/voice/transcribe/ endpoint"""
        mock_auth.return_value = MagicMock(id='test-user-id', email='test@test.com')
        mock_transcribe.return_value = {
            'transcription': 'I have chest pain',
            'language': 'en',
            'language_name': 'English'
        }
        
        response = self.client.post(
            '/api/voice/transcribe/',
            data=json.dumps({
                'audio': 'base64audiodata',
                'mime_type': 'audio/webm'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.mock_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['transcription'], 'I have chest pain')

    @patch('api.decorators.get_supabase_user')
    def test_voice_transcribe_no_audio(self, mock_auth):
        """Test transcribe endpoint with missing audio"""
        mock_auth.return_value = MagicMock(id='test-user-id', email='test@test.com')
        
        response = self.client.post(
            '/api/voice/transcribe/',
            data=json.dumps({}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.mock_token}'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('No audio', response.json()['detail'])

    @patch('api.decorators.get_supabase_user')
    @patch('api.voice_service.get_conversation_response')
    def test_voice_conversation_endpoint(self, mock_conv, mock_auth):
        """Test /api/voice/conversation/ endpoint"""
        mock_auth.return_value = MagicMock(id='test-user-id', email='test@test.com')
        mock_conv.return_value = 'How long have you been experiencing this pain?'
        
        response = self.client.post(
            '/api/voice/conversation/',
            data=json.dumps({
                'message': 'I have chest pain',
                'history': [],
                'language': 'en'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.mock_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('pain', data['response'].lower())

    @patch('api.decorators.get_supabase_user')
    @patch('api.voice_service.get_conversation_response')
    def test_voice_conversation_completion_detection(self, mock_conv, mock_auth):
        """Test that conversation completion is detected"""
        mock_auth.return_value = MagicMock(id='test-user-id', email='test@test.com')
        mock_conv.return_value = 'Thank you for sharing. I have enough information to create a summary.'
        
        response = self.client.post(
            '/api/voice/conversation/',
            data=json.dumps({
                'message': 'That is all',
                'history': [
                    {'role': 'user', 'content': 'chest pain'},
                    {'role': 'assistant', 'content': 'duration?'},
                    {'role': 'user', 'content': '2 days'},
                ],
                'language': 'en'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.mock_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['is_complete'])

    @patch('api.decorators.get_supabase_user')
    def test_voice_conversation_no_message(self, mock_auth):
        """Test conversation endpoint with missing message"""
        mock_auth.return_value = MagicMock(id='test-user-id', email='test@test.com')
        
        response = self.client.post(
            '/api/voice/conversation/',
            data=json.dumps({'history': []}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.mock_token}'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('No message', response.json()['detail'])

    @patch('api.decorators.get_supabase_user')
    @patch('api.voice_service.text_to_speech')
    def test_voice_tts_endpoint(self, mock_tts, mock_auth):
        """Test /api/voice/tts/ endpoint"""
        mock_auth.return_value = MagicMock(id='test-user-id', email='test@test.com')
        mock_tts.return_value = (base64.b64encode(b'fake-audio-data').decode(), 'audio/wav')
        
        response = self.client.post(
            '/api/voice/tts/',
            data=json.dumps({
                'text': 'How are you feeling today?',
                'language': 'en'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.mock_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('audio', data)

    @patch('api.decorators.get_supabase_user')
    @patch('api.voice_service.text_to_speech')
    def test_voice_tts_failure(self, mock_tts, mock_auth):
        """Test TTS endpoint when generation fails"""
        mock_auth.return_value = MagicMock(id='test-user-id', email='test@test.com')
        mock_tts.return_value = (None, '')
        
        response = self.client.post(
            '/api/voice/tts/',
            data=json.dumps({
                'text': 'Test text',
                'language': 'en'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.mock_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])

    @patch('api.decorators.get_supabase_user')
    def test_voice_tts_no_text(self, mock_auth):
        """Test TTS endpoint with missing text"""
        mock_auth.return_value = MagicMock(id='test-user-id', email='test@test.com')
        
        response = self.client.post(
            '/api/voice/tts/',
            data=json.dumps({}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.mock_token}'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('No text', response.json()['detail'])


class VoiceSummaryIntegrationTests(SimpleTestCase):
    """Integration tests for voice summary endpoint"""

    def setUp(self):
        self.client = Client()
        self.mock_token = 'mock-auth-token'

    @patch('api.decorators.get_supabase_user')
    @patch('api.views.Profile')
    @patch('api.voice_service.generate_symptom_summary')
    def test_voice_summary_endpoint(self, mock_summary, mock_profile_class, mock_auth):
        """Test /api/voice/summary/ endpoint"""
        import uuid
        
        mock_auth.return_value = MagicMock(id=str(uuid.uuid4()), email='test@test.com')
        
        mock_profile = MagicMock()
        mock_profile.full_name = 'Test User'
        mock_profile.onboarding_data = {'age': 30, 'sex': 'male'}
        mock_profile.health_summary = ''
        mock_profile_class.objects.get.return_value = mock_profile
        
        mock_summary.return_value = {
            'chief_complaint': 'Chest pain for 2 days',
            'symptoms': [{'symptom': 'chest pain', 'duration': '2 days'}],
            'summary_for_patient': 'You reported chest pain.',
            'summary_for_doctor': 'Patient presents with chest pain, 2 days.',
            'recommended_urgency': 'urgent',
            'suggested_specialty': 'cardiology'
        }
        
        response = self.client.post(
            '/api/voice/summary/',
            data=json.dumps({
                'history': [
                    {'role': 'user', 'content': 'I have chest pain'},
                    {'role': 'assistant', 'content': 'How long?'},
                    {'role': 'user', 'content': '2 days'},
                ]
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.mock_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['summary']['recommended_urgency'], 'urgent')

    @patch('api.decorators.get_supabase_user')
    @patch('api.views.Profile')
    def test_voice_summary_no_history(self, mock_profile_class, mock_auth):
        """Test summary endpoint with missing history"""
        import uuid
        mock_auth.return_value = MagicMock(id=str(uuid.uuid4()), email='test@test.com')
        
        mock_profile = MagicMock()
        mock_profile.full_name = 'Test User'
        mock_profile.onboarding_data = {}
        mock_profile.health_summary = ''
        mock_profile_class.objects.get.return_value = mock_profile
        
        response = self.client.post(
            '/api/voice/summary/',
            data=json.dumps({'history': []}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.mock_token}'
        )
        
        self.assertEqual(response.status_code, 400)


class VoiceUrgencyTests(SimpleTestCase):
    """Tests for urgency detection in voice summaries"""

    @patch('api.voice_service.genai')
    @patch('api.voice_service.settings')
    def test_emergency_urgency_detection(self, mock_settings, mock_genai):
        """Test emergency symptoms are flagged correctly"""
        from api.voice_service import generate_symptom_summary
        
        mock_settings.GEMINI_API_KEY = 'test-key'
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            'chief_complaint': 'Severe chest pain radiating to arm',
            'symptoms': [{'symptom': 'chest pain', 'severity': '10/10'}],
            'summary_for_patient': 'Please seek immediate medical attention.',
            'summary_for_doctor': 'Possible MI. Urgent evaluation needed.',
            'recommended_urgency': 'emergency',
            'suggested_specialty': 'cardiology'
        })
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        
        result = generate_symptom_summary(
            [{'role': 'user', 'content': 'severe chest pain going to my arm'}],
            {'name': 'Test'}
        )
        
        self.assertEqual(result['recommended_urgency'], 'emergency')

    @patch('api.voice_service.genai')
    @patch('api.voice_service.settings')
    def test_routine_urgency_detection(self, mock_settings, mock_genai):
        """Test routine symptoms are flagged correctly"""
        from api.voice_service import generate_symptom_summary
        
        mock_settings.GEMINI_API_KEY = 'test-key'
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            'chief_complaint': 'Mild cold symptoms',
            'symptoms': [{'symptom': 'runny nose', 'severity': '2/10'}],
            'summary_for_patient': 'Rest and stay hydrated.',
            'summary_for_doctor': 'Upper respiratory infection.',
            'recommended_urgency': 'routine',
            'suggested_specialty': 'general'
        })
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response
        
        result = generate_symptom_summary(
            [{'role': 'user', 'content': 'I have a runny nose'}],
            {'name': 'Test'}
        )
        
        self.assertEqual(result['recommended_urgency'], 'routine')

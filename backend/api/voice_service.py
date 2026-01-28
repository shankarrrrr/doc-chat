"""
Voice-based Symptom Collection Service using Gemini Audio
Handles audio transcription, conversation, and symptom summary generation.
"""

import json
import base64
import re
import google.generativeai as genai
from django.conf import settings


SYMPTOM_COLLECTION_PROMPT = """You are a professional medical assistant collecting symptoms from a patient.
Your role is to:
1. Listen to the patient describe their symptoms
2. Ask clear follow-up questions (max 3-4 questions)
3. Be professional and efficient
4. Respond in the SAME language the patient uses

Guidelines:
- Ask about: duration, severity (1-10), location, what makes it better/worse
- Keep responses brief and direct
- Don't diagnose, just collect information
- Be professional, not overly emotional or sympathetic

Current conversation context:
{context}

Patient said: {user_input}

Respond professionally in the same language and ask a relevant follow-up question if needed.
If you have enough information (after 3-4 exchanges), say "Thank you. I have collected the necessary information for your doctor."
"""

SUMMARY_PROMPT = """Based on this symptom collection conversation, create a structured medical summary.

Conversation:
{conversation}

Patient Info:
- Name: {patient_name}
- Age: {age}
- Gender: {gender}

Create a JSON response with:
{{
    "chief_complaint": "Main symptom in patient's words",
    "symptoms": [
        {{
            "symptom": "symptom name",
            "duration": "how long",
            "severity": "1-10 or description",
            "location": "body part if applicable",
            "character": "sharp, dull, burning, etc.",
            "aggravating_factors": "what makes it worse",
            "relieving_factors": "what makes it better"
        }}
    ],
    "associated_symptoms": ["list of related symptoms mentioned"],
    "patient_concerns": "what worries the patient most",
    "recommended_urgency": "routine|soon|urgent|emergency",
    "suggested_specialty": "general|cardiology|neurology|etc.",
    "summary_for_patient": "A friendly 2-3 sentence summary for the patient",
    "summary_for_doctor": "A clinical summary for the doctor (SOAP format style)",
    "language_detected": "language the patient spoke in"
}}

Return ONLY valid JSON, no markdown.
"""


def configure_genai():
    """Configure Gemini API."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise Exception('Gemini API key not configured')
    genai.configure(api_key=api_key)


def transcribe_audio(audio_base64: str, mime_type: str = 'audio/webm') -> dict:
    """
    Transcribe audio using Sarvam AI (better for Indian languages).
    Returns transcription and detected language.
    """
    import requests
    import tempfile
    import os
    
    sarvam_api_key = getattr(settings, 'SARVAM_API_KEY', None)
    
    if sarvam_api_key:
        try:
            audio_bytes = base64.b64decode(audio_base64)
            
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name
            
            try:
                with open(temp_path, 'rb') as audio_file:
                    response = requests.post(
                        'https://api.sarvam.ai/speech-to-text',
                        headers={'API-Subscription-Key': sarvam_api_key},
                        files={'file': ('audio.webm', audio_file, mime_type)},
                        data={'model': 'saarika:v2.5', 'with_timestamps': 'false'},
                        timeout=30
                    )
                
                if response.status_code == 200:
                    data = response.json()
                    transcript = data.get('transcript', '')
                    lang_code = data.get('language_code', 'hi-IN')
                    
                    print(f"STT: detected lang_code={lang_code}, transcript={transcript[:80] if transcript else 'empty'}...")
                    
                    lang_map = {
                        'hi-IN': ('hi', 'Hindi'), 'ta-IN': ('ta', 'Tamil'),
                        'te-IN': ('te', 'Telugu'), 'bn-IN': ('bn', 'Bengali'),
                        'kn-IN': ('kn', 'Kannada'), 'gu-IN': ('gu', 'Gujarati'),
                        'ml-IN': ('ml', 'Malayalam'), 'mr-IN': ('mr', 'Marathi'),
                        'pa-IN': ('pa', 'Punjabi'), 'od-IN': ('or', 'Odia'),
                        'en-IN': ('en', 'English')
                    }
                    lang_info = lang_map.get(lang_code, ('hi', 'Hindi'))
                    
                    return {
                        'transcription': transcript,
                        'language': lang_info[0],
                        'language_name': lang_info[1]
                    }
                else:
                    print(f"STT error: status={response.status_code}, body={response.text[:200]}")
            finally:
                os.unlink(temp_path)
        except Exception as e:
            print(f"Sarvam STT error: {e}")
    
    # Fallback to Gemini
    configure_genai()
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = """Transcribe this audio exactly as spoken.
    Return JSON with:
    {
        "transcription": "exact transcription",
        "language": "detected language code (e.g., hi, en, ta, te, bn, mr)",
        "language_name": "language name in English"
    }
    Return ONLY valid JSON."""
    
    response = model.generate_content([
        prompt,
        {
            'mime_type': mime_type,
            'data': audio_base64
        }
    ])
    
    text = response.text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1] if '\n' in text else text[3:]
    if text.endswith('```'):
        text = text[:-3]
    
    try:
        return json.loads(text.strip())
    except:
        return {
            'transcription': response.text,
            'language': 'unknown',
            'language_name': 'Unknown'
        }


def get_conversation_response(user_input: str, conversation_history: list, language: str = 'en') -> str:
    """
    Get AI response for symptom collection conversation.
    Responds in the same language as the user.
    """
    configure_genai()
    
    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        generation_config={'temperature': 0.7, 'max_output_tokens': 1500}
    )
    
    context = "\n".join([
        f"{'Patient' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
        for msg in conversation_history[-6:]  # Last 6 messages for context
    ])
    
    prompt = SYMPTOM_COLLECTION_PROMPT.format(
        context=context or "Starting conversation",
        user_input=user_input
    )
    
    if language != 'en':
        prompt += f"\n\nIMPORTANT: Respond in {language} language as the patient is speaking in {language}."
    
    response = model.generate_content(prompt)
    return response.text.strip()


def generate_symptom_summary(conversation_history: list, patient_info: dict) -> dict:
    """
    Generate structured symptom summary from conversation.
    """
    configure_genai()
    
    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        generation_config={'temperature': 0.2, 'max_output_tokens': 2000}
    )
    
    conversation_text = "\n".join([
        f"{'Patient' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
        for msg in conversation_history
    ])
    
    prompt = SUMMARY_PROMPT.format(
        conversation=conversation_text,
        patient_name=patient_info.get('name', 'Unknown'),
        age=patient_info.get('age', 'Unknown'),
        gender=patient_info.get('gender', 'Unknown')
    )
    
    response = model.generate_content(prompt)
    text = response.text.strip()
    
    if text.startswith('```'):
        text = text.split('\n', 1)[1] if '\n' in text else text[3:]
    if text.endswith('```'):
        text = text[:-3]
    
    try:
        return json.loads(text.strip())
    except:
        return {
            'chief_complaint': 'Unable to parse symptoms',
            'symptoms': [],
            'summary_for_patient': 'Please describe your symptoms again.',
            'summary_for_doctor': conversation_text,
            'recommended_urgency': 'routine'
        }


def text_to_speech(text: str, language: str = 'en') -> tuple[str | None, str]:
    """
    Convert text to speech using Sarvam AI (for Indian languages) or Gemini TTS.
    Returns tuple of (base64 encoded audio, mime_type).
    """
    import requests
    
    # Map language codes to Sarvam language codes
    indian_lang_map = {
        'hi': 'hi-IN',  # Hindi
        'ta': 'ta-IN',  # Tamil
        'te': 'te-IN',  # Telugu
        'bn': 'bn-IN',  # Bengali
        'kn': 'kn-IN',  # Kannada
        'gu': 'gu-IN',  # Gujarati
        'ml': 'ml-IN',  # Malayalam
        'mr': 'mr-IN',  # Marathi
        'pa': 'pa-IN',  # Punjabi
        'or': 'od-IN',  # Odia
    }
    
    # Use Sarvam AI for Indian languages (much better accent)
    sarvam_api_key = getattr(settings, 'SARVAM_API_KEY', None)
    is_indian = language in indian_lang_map
    
    if is_indian and sarvam_api_key:
        try:
            target_lang = indian_lang_map.get(language, 'hi-IN')
            
            # Use professional voice - arya (male) or manisha (female) work well across languages
            speaker = 'arya'
            print(f"TTS: language={language}, target_lang={target_lang}, speaker={speaker}")
            
            response = requests.post(
                'https://api.sarvam.ai/text-to-speech',
                headers={
                    'API-Subscription-Key': sarvam_api_key,
                    'Content-Type': 'application/json'
                },
                json={
                    'inputs': [text],
                    'target_language_code': target_lang,
                    'speaker': speaker,
                    'model': 'bulbul:v2',
                    'enable_preprocessing': True,
                    'pace': 1.0,
                    'loudness': 1.1,
                    'speech_sample_rate': 22050
                },
                timeout=30
            )
            
            print(f"TTS response status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if 'audios' in data and data['audios']:
                    audio_base64 = data['audios'][0]
                    print(f"TTS SUCCESS: Using Sarvam with speaker={speaker}")
                    return audio_base64, 'audio/wav'
                else:
                    print(f"TTS: No audio in response: {data}")
            else:
                print(f"TTS error response: {response.text[:200]}")
        except Exception as e:
            print(f"Sarvam TTS error: {e}")
    
    # Fallback to Gemini TTS for English or if Sarvam fails
    configure_genai()
    
    try:
        from google import genai as genai_new
        from google.genai import types
        import wave
        import io
        
        client = genai_new.Client(api_key=settings.GEMINI_API_KEY)
        
        response = client.models.generate_content(
            model='gemini-2.5-flash-preview-tts',
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=['AUDIO'],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name='Kore'
                        )
                    )
                )
            )
        )
        
        if response.candidates and response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            pcm_data = part.inline_data.data
            
            # Convert PCM to WAV for browser playback
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(24000)
                wav_file.writeframes(pcm_data)
            
            wav_buffer.seek(0)
            wav_data = wav_buffer.read()
            return base64.b64encode(wav_data).decode('utf-8'), 'audio/wav'
    except Exception as e:
        print(f"Gemini TTS error: {e}")
    
    return None, ''

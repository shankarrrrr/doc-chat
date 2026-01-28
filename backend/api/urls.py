from django.urls import path

from .views import (
    health, me, onboarding, parse_documents, chat_sessions, 
    chat_session_detail, chat_send, recommendations, place_details, 
    medical_records, analyze_ecg, appointments, get_appointment, cancel_appointment,
    call_response_webhook, call_status_webhook, call_retry_webhook,
    doctor_login, doctor_patients, doctor_patient_detail, doctor_generate_summary,
    doctor_update_patient, voice_transcribe, voice_tts, voice_conversation, voice_summary
)

urlpatterns = [
    path('health/', health, name='health'),
    path('me/', me, name='me'),
    path('onboarding/', onboarding, name='onboarding'),
    path('parse-documents/', parse_documents, name='parse_documents'),
    path('records/', medical_records, name='medical_records'),
    path('ecg/analyze/', analyze_ecg, name='analyze_ecg'),
    path('chat/sessions/', chat_sessions, name='chat_sessions'),
    path('chat/sessions/<int:session_id>/', chat_session_detail, name='chat_session_detail'),
    path('chat/sessions/<int:session_id>/send/', chat_send, name='chat_send'),
    path('recommendations/', recommendations, name='recommendations'),
    path('place/<str:place_id>/', place_details, name='place_details'),
    
    # Appointment booking endpoints
    path('appointments/', appointments, name='appointments'),
    path('appointments/<int:appointment_id>/', get_appointment, name='get_appointment'),
    path('appointments/<int:appointment_id>/cancel/', cancel_appointment, name='cancel_appointment'),
    
    # Twilio webhooks (for real calls)
    path('appointments/call-response/<int:appointment_id>/', call_response_webhook, name='call_response_webhook'),
    path('appointments/call-status/<int:appointment_id>/', call_status_webhook, name='call_status_webhook'),
    path('appointments/call-retry/<int:appointment_id>/', call_retry_webhook, name='call_retry_webhook'),
    
    # Doctor dashboard endpoints
    path('doctor/login/', doctor_login, name='doctor_login'),
    path('doctor/patients/', doctor_patients, name='doctor_patients'),
    path('doctor/patients/<str:patient_id>/', doctor_patient_detail, name='doctor_patient_detail'),
    path('doctor/patients/<str:patient_id>/summary/', doctor_generate_summary, name='doctor_generate_summary'),
    path('doctor/patients/<str:patient_id>/update/', doctor_update_patient, name='doctor_update_patient'),
    
    # Voice symptom collection endpoints
    path('voice/transcribe/', voice_transcribe, name='voice_transcribe'),
    path('voice/tts/', voice_tts, name='voice_tts'),
    path('voice/conversation/', voice_conversation, name='voice_conversation'),
    path('voice/summary/', voice_summary, name='voice_summary'),
]

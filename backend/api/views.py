import json
import uuid
from typing import Any

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from twilio.twiml.voice_response import VoiceResponse, Gather

from .decorators import supabase_required
from .models import Profile, ChatSession, ChatMessage, Appointment
from .supabase_auth import SupabaseUser
from .ai_service import get_ai_response
from .recommendations_service import get_full_recommendations, get_place_details


def health(_request):
    return JsonResponse({'status': 'ok'})


def _profile_response(user: SupabaseUser, profile: Profile) -> JsonResponse:
    meta = user.user_metadata or {}
    meta_name = meta.get('full_name') or meta.get('name')
    name = profile.full_name or (meta_name if isinstance(meta_name, str) else None)

    onboarding_data = profile.onboarding_data
    if not isinstance(onboarding_data, dict):
        onboarding_data = {}

    return JsonResponse(
        {
            'user': {
                'id': user.id,
                'email': user.email,
                'name': name,
            },
            'profile': {
                'onboarding_completed': profile.onboarding_completed,
                'onboarding_data': onboarding_data,
                'health_summary': profile.health_summary or '',
            },
        }
    )


@csrf_exempt
@require_http_methods(['GET'])
@supabase_required
def me(request):
    user: SupabaseUser = request.supabase_user  # type: ignore[attr-defined]

    try:
        supabase_uid = uuid.UUID(user.id)
    except ValueError:
        return JsonResponse({'detail': 'Invalid user id'}, status=400)

    meta = user.user_metadata or {}
    meta_name = meta.get('full_name') or meta.get('name')

    defaults: dict[str, Any] = {
        'email': user.email or '',
        'full_name': meta_name if isinstance(meta_name, str) else '',
    }

    profile, _created = Profile.objects.get_or_create(
        supabase_uid=supabase_uid,
        defaults=defaults,
    )

    updated_fields: list[str] = []
    if user.email and profile.email != user.email:
        profile.email = user.email
        updated_fields.append('email')

    if not profile.full_name and isinstance(meta_name, str) and meta_name:
        profile.full_name = meta_name
        updated_fields.append('full_name')

    if updated_fields:
        profile.save(update_fields=updated_fields + ['updated_at'])

    return _profile_response(user, profile)


@csrf_exempt
@require_http_methods(['POST'])
@supabase_required
def onboarding(request):
    user: SupabaseUser = request.supabase_user  # type: ignore[attr-defined]

    try:
        supabase_uid = uuid.UUID(user.id)
    except ValueError:
        return JsonResponse({'detail': 'Invalid user id'}, status=400)

    try:
        payload = json.loads((request.body or b'{}').decode('utf-8'))
    except ValueError:
        return JsonResponse({'detail': 'Invalid JSON'}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({'detail': 'Invalid JSON'}, status=400)

    full_name = payload.get('full_name')
    if not isinstance(full_name, str) or not full_name.strip():
        return JsonResponse({'detail': 'full_name is required'}, status=400)

    allowed_keys = {
        'full_name',
        'age',
        'sex',
        'allergies',
        'conditions',
        'medications',
        'height',
        'weight',
        'blood_type',
        'smoking_status',
        'alcohol_consumption',
        'exercise_frequency',
        'diet_type',
        'sleep_hours',
        'stress_level',
        'family_history',
        'health_goals',
        'emergency_contact_name',
        'emergency_contact_phone',
        # New unified record fields
        'medical_history',
        'past_reports',
        'prescriptions',
        'symptoms_current',
        'symptoms_past',
        'location',
        'blood_pressure',
        'heart_rate',
        'temperature_c',
        'spo2',
    }
    onboarding_data: dict[str, Any] = {
        key: value for key, value in payload.items() if key in allowed_keys
    }

    age = onboarding_data.get('age')
    if age is not None and not isinstance(age, int):
        return JsonResponse({'detail': 'age must be an integer'}, status=400)

    profile, _created = Profile.objects.get_or_create(
        supabase_uid=supabase_uid,
        defaults={
            'email': user.email or '',
        },
    )

    profile.full_name = full_name.strip()
    profile.onboarding_data = onboarding_data
    profile.onboarding_completed = True
    if user.email:
        profile.email = user.email

    profile.save(
        update_fields=[
            'email',
            'full_name',
            'onboarding_data',
            'onboarding_completed',
            'updated_at',
        ]
    )

    return _profile_response(user, profile)


@csrf_exempt
@require_http_methods(['POST'])
@supabase_required
def parse_documents(request):
    """Parse uploaded medical documents using Gemini and create medical records."""
    from .ai_service import parse_document_to_records
    from .models import MedicalRecord
    from datetime import datetime
    
    user: SupabaseUser = request.supabase_user  # type: ignore[attr-defined]

    try:
        supabase_uid = uuid.UUID(user.id)
    except ValueError:
        return JsonResponse({'detail': 'Invalid user id'}, status=400)

    try:
        profile = Profile.objects.get(supabase_uid=supabase_uid)
    except Profile.DoesNotExist:
        return JsonResponse({'detail': 'Profile not found'}, status=404)

    files = request.FILES.getlist('documents')
    if not files:
        return JsonResponse({'detail': 'No documents provided'}, status=400)

    # Read file contents
    documents_list = []
    filenames = []
    for f in files:
        if f.size > 10 * 1024 * 1024:  # 10MB limit
            return JsonResponse({'detail': f'File {f.name} exceeds 10MB limit'}, status=400)
        
        filenames.append(f.name)
        content_type = f.content_type or ''
        if 'pdf' in content_type:
            try:
                text = f.read().decode('utf-8', errors='ignore')
            except:
                text = f"[PDF file: {f.name}]"
        elif 'image' in content_type:
            import base64
            image_data = base64.b64encode(f.read()).decode('utf-8')
            documents_list.append({
                'type': 'image',
                'name': f.name,
                'mime_type': content_type,
                'data': image_data
            })
            continue
        else:
            text = f.read().decode('utf-8', errors='ignore')
        
        documents_list.append({
            'type': 'text',
            'name': f.name,
            'content': text
        })

    current_summary = profile.health_summary or ''

    # Parse documents with Gemini to get individual records
    try:
        parsed_result = parse_document_to_records(documents_list, current_summary)
    except Exception as e:
        return JsonResponse({'detail': f'Failed to parse documents: {str(e)}'}, status=500)

    # Create medical records from parsed data
    created_records = []
    records_data = parsed_result.get('records', [])
    
    for record_data in records_data:
        # Parse date if provided
        record_date = None
        if record_data.get('record_date'):
            try:
                record_date = datetime.strptime(record_data['record_date'], '%Y-%m-%d').date()
            except:
                pass
        
        # Validate category
        valid_categories = ['lab_reports', 'prescriptions', 'diagnoses', 'vitals', 'imaging', 'other']
        category = record_data.get('category', 'other')
        if category not in valid_categories:
            category = 'other'
        
        # Validate status
        valid_statuses = ['normal', 'attention', 'critical']
        status = record_data.get('status', 'normal')
        if status not in valid_statuses:
            status = 'normal'
        
        record = MedicalRecord.objects.create(
            profile=profile,
            category=category,
            title=record_data.get('title') or 'Untitled Record',
            summary=record_data.get('summary') or '',
            details=record_data.get('details') or {},
            doctor=record_data.get('doctor') or '',
            facility=record_data.get('facility') or '',
            record_date=record_date,
            status=status,
            source_filename=', '.join(filenames)
        )
        created_records.append(record)

    # Update health summary
    health_summary = parsed_result.get('health_summary')
    if health_summary:
        profile.health_summary = health_summary
    
    # Update profile with any extracted info
    profile_updates = parsed_result.get('profile_updates', {})
    current_data = profile.onboarding_data or {}
    for key, value in profile_updates.items():
        if value and value != 'Not provided' and str(value).strip():
            current_data[key] = value
    
    profile.onboarding_data = current_data
    profile.save(update_fields=['onboarding_data', 'health_summary', 'updated_at'])

    return JsonResponse({
        'success': True,
        'records_created': len(created_records),
        'records': [
            {
                'id': r.id,
                'category': r.category,
                'title': r.title,
                'summary': r.summary,
                'status': r.status,
            }
            for r in created_records
        ],
        'profile': {
            'onboarding_completed': profile.onboarding_completed,
            'onboarding_data': profile.onboarding_data,
            'health_summary': profile.health_summary or '',
        }
    })


@csrf_exempt
@require_http_methods(['GET', 'POST'])
@supabase_required
def chat_sessions(request):
    user: SupabaseUser = request.supabase_user  # type: ignore[attr-defined]

    try:
        supabase_uid = uuid.UUID(user.id)
    except ValueError:
        return JsonResponse({'detail': 'Invalid user id'}, status=400)

    try:
        profile = Profile.objects.get(supabase_uid=supabase_uid)
    except Profile.DoesNotExist:
        return JsonResponse({'detail': 'Profile not found'}, status=404)

    if request.method == 'GET':
        sessions = ChatSession.objects.filter(profile=profile)
        return JsonResponse({
            'sessions': [
                {
                    'id': s.id,
                    'title': s.title or f'Chat {s.id}',
                    'created_at': s.created_at.isoformat(),
                    'updated_at': s.updated_at.isoformat(),
                }
                for s in sessions
            ]
        })

    try:
        payload = json.loads((request.body or b'{}').decode('utf-8'))
    except ValueError:
        payload = {}

    session = ChatSession.objects.create(
        profile=profile,
        title=payload.get('title', '')
    )
    return JsonResponse({
        'id': session.id,
        'title': session.title,
        'created_at': session.created_at.isoformat(),
    }, status=201)


@csrf_exempt
@require_http_methods(['GET', 'DELETE'])
@supabase_required
def chat_session_detail(request, session_id: int):
    user: SupabaseUser = request.supabase_user  # type: ignore[attr-defined]

    try:
        supabase_uid = uuid.UUID(user.id)
    except ValueError:
        return JsonResponse({'detail': 'Invalid user id'}, status=400)

    try:
        profile = Profile.objects.get(supabase_uid=supabase_uid)
        session = ChatSession.objects.get(id=session_id, profile=profile)
    except (Profile.DoesNotExist, ChatSession.DoesNotExist):
        return JsonResponse({'detail': 'Not found'}, status=404)

    if request.method == 'DELETE':
        session.delete()
        return JsonResponse({'detail': 'Deleted'})

    messages = session.messages.all()
    return JsonResponse({
        'id': session.id,
        'title': session.title,
        'messages': [
            {
                'id': m.id,
                'role': m.role,
                'content': m.content,
                'created_at': m.created_at.isoformat(),
            }
            for m in messages
        ]
    })


@csrf_exempt
@require_http_methods(['POST'])
@supabase_required
def chat_send(request, session_id: int):
    user: SupabaseUser = request.supabase_user  # type: ignore[attr-defined]

    try:
        supabase_uid = uuid.UUID(user.id)
    except ValueError:
        return JsonResponse({'detail': 'Invalid user id'}, status=400)

    try:
        profile = Profile.objects.get(supabase_uid=supabase_uid)
        session = ChatSession.objects.get(id=session_id, profile=profile)
    except (Profile.DoesNotExist, ChatSession.DoesNotExist):
        return JsonResponse({'detail': 'Not found'}, status=404)

    try:
        payload = json.loads((request.body or b'{}').decode('utf-8'))
    except ValueError:
        return JsonResponse({'detail': 'Invalid JSON'}, status=400)

    message_content = payload.get('message', '').strip()
    if not message_content:
        return JsonResponse({'detail': 'message is required'}, status=400)

    user_message = ChatMessage.objects.create(
        session=session,
        role='user',
        content=message_content
    )

    all_messages = list(session.messages.values('role', 'content'))

    # Get medical records for context
    from .models import MedicalRecord
    medical_records = list(MedicalRecord.objects.filter(profile=profile).values(
        'category', 'title', 'summary', 'details', 'status', 'record_date'
    )[:20])

    try:
        ai_response_text = get_ai_response(
            all_messages,
            profile.onboarding_data or {},
            profile.health_summary or '',
            medical_records
        )
    except Exception as e:
        return JsonResponse({'detail': str(e)}, status=500)

    ai_message = ChatMessage.objects.create(
        session=session,
        role='ai',
        content=ai_response_text
    )

    if not session.title and len(all_messages) <= 2:
        session.title = message_content[:50]
        session.save(update_fields=['title', 'updated_at'])
    else:
        session.save(update_fields=['updated_at'])

    return JsonResponse({
        'user_message': {
            'id': user_message.id,
            'role': user_message.role,
            'content': user_message.content,
            'created_at': user_message.created_at.isoformat(),
        },
        'ai_message': {
            'id': ai_message.id,
            'role': ai_message.role,
            'content': ai_message.content,
            'created_at': ai_message.created_at.isoformat(),
        }
    })


@csrf_exempt
@require_http_methods(['GET'])
@supabase_required
def recommendations(request):
    """Get hospital and doctor recommendations based on patient profile."""
    user: SupabaseUser = request.supabase_user  # type: ignore[attr-defined]

    try:
        supabase_uid = uuid.UUID(user.id)
    except ValueError:
        return JsonResponse({'detail': 'Invalid user id'}, status=400)

    try:
        profile = Profile.objects.get(supabase_uid=supabase_uid)
    except Profile.DoesNotExist:
        return JsonResponse({'detail': 'Profile not found'}, status=404)

    user_lat = request.GET.get('lat')
    user_lng = request.GET.get('lng')

    lat = float(user_lat) if user_lat else None
    lng = float(user_lng) if user_lng else None

    result = get_full_recommendations(profile.onboarding_data or {}, lat, lng)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(['GET'])
@supabase_required
def place_details(request, place_id: str):
    """Get detailed information about a specific place."""
    details = get_place_details(place_id)
    if not details:
        return JsonResponse({'detail': 'Place not found'}, status=404)
    return JsonResponse(details)


@csrf_exempt
@require_http_methods(['GET'])
@supabase_required
def medical_records(request):
    """Get all medical records for the authenticated user."""
    from .models import MedicalRecord
    
    user: SupabaseUser = request.supabase_user  # type: ignore[attr-defined]

    try:
        supabase_uid = uuid.UUID(user.id)
    except ValueError:
        return JsonResponse({'detail': 'Invalid user id'}, status=400)

    try:
        profile = Profile.objects.get(supabase_uid=supabase_uid)
    except Profile.DoesNotExist:
        return JsonResponse({'detail': 'Profile not found'}, status=404)

    category = request.GET.get('category')
    
    records = MedicalRecord.objects.filter(profile=profile)
    if category and category != 'all':
        records = records.filter(category=category)
    
    records_list = []
    for r in records:
        records_list.append({
            'id': r.id,
            'category': r.category,
            'title': r.title,
            'summary': r.summary,
            'details': r.details,
            'doctor': r.doctor,
            'facility': r.facility,
            'record_date': r.record_date.isoformat() if r.record_date else None,
            'status': r.status,
            'source_filename': r.source_filename,
            'created_at': r.created_at.isoformat(),
        })
    
    # Get counts by category
    all_records = MedicalRecord.objects.filter(profile=profile)
    counts = {
        'all': all_records.count(),
        'lab_reports': all_records.filter(category='lab_reports').count(),
        'prescriptions': all_records.filter(category='prescriptions').count(),
        'diagnoses': all_records.filter(category='diagnoses').count(),
        'vitals': all_records.filter(category='vitals').count(),
        'imaging': all_records.filter(category='imaging').count(),
        'other': all_records.filter(category='other').count(),
    }
    
    return JsonResponse({
        'records': records_list,
        'counts': counts,
    })


@csrf_exempt
@require_http_methods(['POST'])
@supabase_required
def analyze_ecg(request):
    """Analyze uploaded ECG image and predict cardiovascular disease."""
    from .models import MedicalRecord
    from datetime import datetime
    import tempfile
    import os
    
    user: SupabaseUser = request.supabase_user

    try:
        supabase_uid = uuid.UUID(user.id)
    except ValueError:
        return JsonResponse({'detail': 'Invalid user id'}, status=400)

    try:
        profile = Profile.objects.get(supabase_uid=supabase_uid)
    except Profile.DoesNotExist:
        return JsonResponse({'detail': 'Profile not found'}, status=404)

    ecg_file = request.FILES.get('ecg_image')
    if not ecg_file:
        return JsonResponse({'detail': 'No ECG image provided'}, status=400)
    
    if ecg_file.size > 10 * 1024 * 1024:
        return JsonResponse({'detail': 'File exceeds 10MB limit'}, status=400)
    
    allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
    if ecg_file.content_type not in allowed_types:
        return JsonResponse({'detail': 'Only JPEG and PNG images are supported'}, status=400)

    try:
        from .ecg_service import ECGPredictor
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            for chunk in ecg_file.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name
        
        try:
            predictor = ECGPredictor()
            result = predictor.predict_from_ecg_image(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
        if not result.get('success'):
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'ECG analysis failed'),
                'prediction': {
                    'label': 'Error',
                    'message': result.get('prediction_message', 'Failed to analyze ECG')
                }
            }, status=500)
        
        record = MedicalRecord.objects.create(
            profile=profile,
            category='imaging',
            title=f"ECG Analysis - {result['prediction_label']}",
            summary=result['prediction_message'],
            details={
                'prediction_code': result['prediction_code'],
                'prediction_label': result['prediction_label'],
                'confidence': result.get('confidence'),
                'features_extracted': result.get('num_features'),
                'analysis_type': 'Cardiovascular Disease Detection',
            },
            doctor='AI Analysis',
            facility='DYP Health Platform',
            record_date=datetime.now().date(),
            status=result.get('status', 'normal'),
            source_filename=ecg_file.name
        )
        
        # Update health summary with ECG findings
        current_summary = profile.health_summary or ''
        ecg_finding = f"\n\nECG Analysis ({datetime.now().strftime('%Y-%m-%d')}): {result['prediction_label']}"
        if result.get('confidence'):
            ecg_finding += f" (Confidence: {result['confidence']:.1f}%)"
        ecg_finding += f". {result['prediction_message']}"
        
        if 'ECG Analysis' not in current_summary:
            profile.health_summary = current_summary + ecg_finding
        else:
            # Update existing ECG section
            lines = current_summary.split('\n\n')
            updated_lines = [l for l in lines if not l.startswith('ECG Analysis')]
            profile.health_summary = '\n\n'.join(updated_lines) + ecg_finding
        
        profile.save(update_fields=['health_summary', 'updated_at'])
        
        return JsonResponse({
            'success': True,
            'prediction': {
                'code': result['prediction_code'],
                'label': result['prediction_label'],
                'message': result['prediction_message'],
                'confidence': result.get('confidence'),
                'status': result.get('status', 'normal'),
            },
            'record': {
                'id': record.id,
                'title': record.title,
                'category': record.category,
            },
            'profile': {
                'health_summary': profile.health_summary,
            }
        })
        
    except ImportError as e:
        return JsonResponse({
            'success': False,
            'error': f'ECG analysis dependencies not installed: {str(e)}',
            'prediction': {
                'label': 'Error',
                'message': 'ECG analysis service unavailable. Required packages not installed.'
            }
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'prediction': {
                'label': 'Error',
                'message': f'ECG analysis failed: {str(e)}'
            }
        }, status=500)


# ============ Appointment Booking Views ============

@csrf_exempt
@require_http_methods(['GET', 'POST'])
@supabase_required
def appointments(request):
    """List appointments or create a new booking request."""
    from .models import Appointment
    from .appointment_service import simulate_appointment_booking
    
    user: SupabaseUser = request.supabase_user
    profile = Profile.objects.get(supabase_uid=user.id)
    
    if request.method == 'GET':
        # List user's appointments
        appointments_qs = Appointment.objects.filter(profile=profile)
        
        status_filter = request.GET.get('status')
        if status_filter:
            appointments_qs = appointments_qs.filter(status=status_filter)
        
        appointments_list = []
        for apt in appointments_qs[:20]:
            appointments_list.append({
                'id': apt.id,
                'hospital_name': apt.hospital_name,
                'hospital_address': apt.hospital_address,
                'status': apt.status,
                'appointment_date': str(apt.appointment_date) if apt.appointment_date else None,
                'appointment_time': str(apt.appointment_time) if apt.appointment_time else None,
                'doctor_name': apt.doctor_name,
                'department': apt.department,
                'purpose': apt.purpose,
                'notes': apt.notes,
                'created_at': apt.created_at.isoformat(),
            })
        
        return JsonResponse({'appointments': appointments_list})
    
    # POST - Create new appointment booking
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid JSON'}, status=400)
    
    hospital_name = data.get('hospital_name')
    if not hospital_name:
        return JsonResponse({'detail': 'hospital_name is required'}, status=400)
    
    # Create appointment record
    appointment = Appointment.objects.create(
        profile=profile,
        hospital_name=hospital_name,
        hospital_address=data.get('hospital_address', ''),
        hospital_phone=data.get('hospital_phone', ''),
        hospital_place_id=data.get('hospital_place_id', ''),
        purpose=data.get('purpose', 'General consultation'),
        status='pending'
    )
    
    # Get patient info for the call
    patient_info = profile.onboarding_data or {}
    patient_info['full_name'] = profile.full_name or profile.email
    
    # Check if real calls are enabled (NGROK_URL is set)
    ngrok_url = getattr(settings, 'NGROK_URL', '').strip("'\"")
    use_real_calls = data.get('use_real_call', False) and ngrok_url
    
    if use_real_calls:
        # Make real Twilio call
        from .appointment_service import initiate_appointment_call
        result = initiate_appointment_call(
            appointment_id=appointment.id,
            hospital_phone=appointment.hospital_phone or '+919876543210',
            patient_info=patient_info,
            purpose=appointment.purpose,
            callback_url=ngrok_url
        )
        # For real calls, return immediately - status updates come via webhooks
        return JsonResponse({
            'success': True,
            'real_call': True,
            'appointment': {
                'id': appointment.id,
                'hospital_name': appointment.hospital_name,
                'status': 'calling',
                'message': 'Call initiated - you will receive a call shortly'
            }
        })
    else:
        # Use simulation mode (no actual Twilio calls)
        result = simulate_appointment_booking(appointment.id, patient_info)
    
    # Refresh appointment from DB
    appointment.refresh_from_db()
    
    return JsonResponse({
        'success': True,
        'appointment': {
            'id': appointment.id,
            'hospital_name': appointment.hospital_name,
            'status': appointment.status,
            'appointment_date': str(appointment.appointment_date) if appointment.appointment_date else None,
            'appointment_time': str(appointment.appointment_time) if appointment.appointment_time else None,
            'doctor_name': appointment.doctor_name,
            'department': appointment.department,
            'notes': appointment.notes,
            'transcript': appointment.call_transcript,
        },
        'message': 'Appointment booking processed'
    })


@csrf_exempt
@require_http_methods(['GET'])
@supabase_required
def get_appointment(request, appointment_id):
    """Get a specific appointment's details."""
    from .models import Appointment
    
    user: SupabaseUser = request.supabase_user
    profile = Profile.objects.get(supabase_uid=user.id)
    
    try:
        appointment = Appointment.objects.get(id=appointment_id, profile=profile)
    except Appointment.DoesNotExist:
        return JsonResponse({'detail': 'Appointment not found'}, status=404)
    
    return JsonResponse({
        'appointment': {
            'id': appointment.id,
            'hospital_name': appointment.hospital_name,
            'hospital_address': appointment.hospital_address,
            'hospital_phone': appointment.hospital_phone,
            'status': appointment.status,
            'appointment_date': str(appointment.appointment_date) if appointment.appointment_date else None,
            'appointment_time': str(appointment.appointment_time) if appointment.appointment_time else None,
            'doctor_name': appointment.doctor_name,
            'department': appointment.department,
            'purpose': appointment.purpose,
            'notes': appointment.notes,
            'call_transcript': appointment.call_transcript,
            'call_duration': appointment.call_duration,
            'created_at': appointment.created_at.isoformat(),
            'updated_at': appointment.updated_at.isoformat(),
        }
    })


@csrf_exempt
@require_http_methods(['POST'])
@supabase_required
def cancel_appointment(request, appointment_id):
    """Cancel an appointment."""
    from .models import Appointment
    
    user: SupabaseUser = request.supabase_user
    profile = Profile.objects.get(supabase_uid=user.id)
    
    try:
        appointment = Appointment.objects.get(id=appointment_id, profile=profile)
    except Appointment.DoesNotExist:
        return JsonResponse({'detail': 'Appointment not found'}, status=404)
    
    if appointment.status in ['cancelled', 'failed']:
        return JsonResponse({'detail': 'Appointment already cancelled or failed'}, status=400)
    
    appointment.status = 'cancelled'
    appointment.notes = (appointment.notes + '\n' if appointment.notes else '') + 'Cancelled by user'
    appointment.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Appointment cancelled',
        'status': appointment.status
    })


# Twilio webhook endpoints (for actual calls - not used in simulation mode)
@csrf_exempt
@require_http_methods(['POST', 'GET'])
def call_response_webhook(request, appointment_id):
    """Handle Twilio call response webhook."""
    from .appointment_service import process_call_response
    
    # Twilio can send data via GET or POST
    if request.method == 'POST':
        speech_result = request.POST.get('SpeechResult', '')
    else:
        speech_result = request.GET.get('SpeechResult', '')
    
    callback_url = request.build_absolute_uri('/')[:-1]  # Base URL without trailing slash
    
    twiml = process_call_response(appointment_id, speech_result, callback_url)
    
    return HttpResponse(twiml, content_type='application/xml')


@csrf_exempt
@require_http_methods(['POST'])
def call_status_webhook(request, appointment_id):
    """Handle Twilio call status webhook."""
    from .appointment_service import update_call_status
    
    call_status = request.POST.get('CallStatus', '')
    call_duration = request.POST.get('CallDuration')
    
    if call_duration:
        try:
            call_duration = int(call_duration)
        except:
            call_duration = None
    
    update_call_status(appointment_id, call_status, call_duration)
    
    return HttpResponse('<Response></Response>', content_type='application/xml')


@csrf_exempt
@require_http_methods(['POST'])
def call_retry_webhook(request, appointment_id):
    """Handle call retry when no response received."""
    from .models import Appointment
    
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        patient_info = appointment.profile.onboarding_data or {}
        patient_info['full_name'] = appointment.profile.full_name
        
        from .appointment_service import generate_ai_response
        
        response = VoiceResponse()
        gather = Gather(
            input='speech',
            action=f'/api/appointments/call-response/{appointment_id}/',
            method='POST',
            speech_timeout='auto',
            language='en-IN'
        )
        
        # Generate a retry message
        retry_msg = "Hello, are you still there? I'm calling to book an appointment."
        gather.say(retry_msg, voice='Polly.Aditi', language='en-IN')
        response.append(gather)
        
        # If still no response, end call
        response.say("I'm sorry, I couldn't reach anyone. Goodbye.",
                    voice='Polly.Aditi', language='en-IN')
        response.hangup()
        
        return HttpResponse(str(response), content_type='application/xml')
        
    except Exception as e:
        response = VoiceResponse()
        response.say("I'm sorry, there was an error. Goodbye.",
                    voice='Polly.Aditi', language='en-IN')
        response.hangup()
        return HttpResponse(str(response), content_type='application/xml')


# ============ Doctor Dashboard Views ============

DOCTOR_PASSWORD = 'doctor123'  # Hardcoded password for demo

@csrf_exempt
@require_http_methods(['POST'])
def doctor_login(request):
    """Doctor login with hardcoded password."""
    try:
        payload = json.loads((request.body or b'{}').decode('utf-8'))
    except ValueError:
        return JsonResponse({'detail': 'Invalid JSON'}, status=400)
    
    password = payload.get('password', '')
    
    if password == DOCTOR_PASSWORD:
        import secrets
        token = secrets.token_hex(32)
        return JsonResponse({
            'success': True,
            'token': token,
            'message': 'Login successful'
        })
    else:
        return JsonResponse({'detail': 'Invalid password'}, status=401)


@csrf_exempt
@require_http_methods(['GET'])
def doctor_patients(request):
    """Get all patients for doctor dashboard."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Doctor '):
        return JsonResponse({'detail': 'Unauthorized'}, status=401)
    
    profiles = Profile.objects.filter(onboarding_completed=True)
    
    patients = []
    for profile in profiles:
        data = profile.onboarding_data or {}
        patients.append({
            'id': str(profile.supabase_uid),
            'name': profile.full_name or profile.email or 'Unknown',
            'email': profile.email,
            'age': data.get('age'),
            'sex': data.get('sex'),
            'conditions': data.get('conditions'),
            'current_symptoms': data.get('symptoms_current'),
            'assigned_at': profile.created_at.isoformat(),
            'notes': '',
        })
    
    return JsonResponse({'patients': patients})


@csrf_exempt
@require_http_methods(['GET'])
def doctor_patient_detail(request, patient_id: str):
    """Get detailed patient information for doctor."""
    from .doctor_service import get_patient_dashboard_data
    
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Doctor '):
        return JsonResponse({'detail': 'Unauthorized'}, status=401)
    
    try:
        patient_uuid = uuid.UUID(patient_id)
        profile = Profile.objects.get(supabase_uid=patient_uuid)
    except (ValueError, Profile.DoesNotExist):
        return JsonResponse({'detail': 'Patient not found'}, status=404)
    
    dashboard_data = get_patient_dashboard_data(profile)
    return JsonResponse(dashboard_data)


@csrf_exempt
@require_http_methods(['POST'])
def doctor_generate_summary(request, patient_id: str):
    """Generate AI case summary for a patient."""
    from .doctor_service import generate_ai_case_summary, get_patient_dashboard_data
    
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Doctor '):
        return JsonResponse({'detail': 'Unauthorized'}, status=401)
    
    try:
        patient_uuid = uuid.UUID(patient_id)
        profile = Profile.objects.get(supabase_uid=patient_uuid)
    except (ValueError, Profile.DoesNotExist):
        return JsonResponse({'detail': 'Patient not found'}, status=404)
    
    try:
        payload = json.loads((request.body or b'{}').decode('utf-8'))
    except ValueError:
        payload = {}
    
    reason = payload.get('reason', '')
    patient_data = get_patient_dashboard_data(profile)
    summary = generate_ai_case_summary(patient_data, reason)
    
    return JsonResponse({'summary': summary})


@csrf_exempt
@require_http_methods(['PUT'])
def doctor_update_patient(request, patient_id: str):
    """Update patient data by doctor."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Doctor '):
        return JsonResponse({'detail': 'Unauthorized'}, status=401)
    
    try:
        patient_uuid = uuid.UUID(patient_id)
        profile = Profile.objects.get(supabase_uid=patient_uuid)
    except (ValueError, Profile.DoesNotExist):
        return JsonResponse({'detail': 'Patient not found'}, status=404)
    
    try:
        payload = json.loads((request.body or b'{}').decode('utf-8'))
    except ValueError:
        return JsonResponse({'detail': 'Invalid JSON'}, status=400)
    
    allowed_fields = {
        'blood_pressure', 'heart_rate', 'temperature_c', 'spo2',
        'height', 'weight', 'symptoms_current', 'symptoms_past',
        'conditions', 'medications', 'allergies', 'medical_history',
        'doctor_notes'
    }
    
    current_data = profile.onboarding_data or {}
    
    for key, value in payload.items():
        if key in allowed_fields:
            current_data[key] = value
    
    profile.onboarding_data = current_data
    profile.save(update_fields=['onboarding_data', 'updated_at'])
    
    from .doctor_service import get_patient_dashboard_data
    return JsonResponse(get_patient_dashboard_data(profile))


# ============ Voice Symptom Collection Views ============

@csrf_exempt
@require_http_methods(['POST'])
@supabase_required
def voice_transcribe(request):
    """Transcribe audio to text using Gemini."""
    from .voice_service import transcribe_audio
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid JSON'}, status=400)
    
    audio_base64 = data.get('audio')
    mime_type = data.get('mime_type', 'audio/webm')
    
    if not audio_base64:
        return JsonResponse({'detail': 'No audio provided'}, status=400)
    
    try:
        result = transcribe_audio(audio_base64, mime_type)
        return JsonResponse({
            'success': True,
            'transcription': result.get('transcription', ''),
            'language': result.get('language', 'en'),
            'language_name': result.get('language_name', 'English')
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
@supabase_required
def voice_tts(request):
    """Convert text to speech using Gemini TTS."""
    from .voice_service import text_to_speech
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid JSON'}, status=400)
    
    text = data.get('text', '')
    language = data.get('language', 'en')
    
    if not text:
        return JsonResponse({'detail': 'No text provided'}, status=400)
    
    try:
        audio_base64, mime_type = text_to_speech(text, language)
        if audio_base64:
            return JsonResponse({
                'success': True,
                'audio': audio_base64,
                'mime_type': mime_type
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'TTS generation failed'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
@supabase_required
def voice_conversation(request):
    """Handle voice conversation for symptom collection."""
    from .voice_service import get_conversation_response
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid JSON'}, status=400)
    
    user_input = data.get('message', '')
    conversation_history = data.get('history', [])
    language = data.get('language', 'en')
    
    if not user_input:
        return JsonResponse({'detail': 'No message provided'}, status=400)
    
    try:
        response = get_conversation_response(user_input, conversation_history, language)
        
        is_complete = any(phrase in response.lower() for phrase in [
            'enough information',
            'create a summary',
            'thank you for sharing',
            'collected the necessary',
            'necessary information',
            'पर्याप्त जानकारी',
            'सारांश बना',
            'आवश्यक जानकारी',
        ])
        
        return JsonResponse({
            'success': True,
            'response': response,
            'is_complete': is_complete
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
@supabase_required
def voice_summary(request):
    """Generate symptom summary from conversation."""
    from .voice_service import generate_symptom_summary
    
    user: SupabaseUser = request.supabase_user
    
    try:
        supabase_uid = uuid.UUID(user.id)
        profile = Profile.objects.get(supabase_uid=supabase_uid)
    except (ValueError, Profile.DoesNotExist):
        return JsonResponse({'detail': 'Profile not found'}, status=404)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid JSON'}, status=400)
    
    conversation_history = data.get('history', [])
    
    if not conversation_history:
        return JsonResponse({'detail': 'No conversation history'}, status=400)
    
    onboarding_data = profile.onboarding_data or {}
    patient_info = {
        'name': profile.full_name or onboarding_data.get('full_name', 'Patient'),
        'age': onboarding_data.get('age'),
        'gender': onboarding_data.get('sex')
    }
    
    try:
        summary = generate_symptom_summary(conversation_history, patient_info)
        
        # Update profile with symptoms
        onboarding_data['symptoms_current'] = summary.get('chief_complaint', '')
        onboarding_data['voice_symptoms'] = summary.get('symptoms', [])
        onboarding_data['symptom_summary'] = summary
        profile.onboarding_data = onboarding_data
        
        # Update health summary
        current_health_summary = profile.health_summary or ''
        voice_summary_text = f"\n\nVoice Symptom Collection: {summary.get('summary_for_doctor', '')}"
        if 'Voice Symptom Collection' not in current_health_summary:
            profile.health_summary = current_health_summary + voice_summary_text
        
        profile.save(update_fields=['onboarding_data', 'health_summary', 'updated_at'])
        
        return JsonResponse({
            'success': True,
            'summary': summary
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

from django.db import models


class Profile(models.Model):
    supabase_uid = models.UUIDField(unique=True)
    email = models.EmailField(blank=True)
    full_name = models.CharField(max_length=255, blank=True)
    onboarding_completed = models.BooleanField(default=False)
    onboarding_data = models.JSONField(default=dict, blank=True)
    health_summary = models.TextField(blank=True, default='')  # AI-generated health summary
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f'{self.email or self.supabase_uid}'


class ChatSession(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self) -> str:
        return f'Chat {self.id} - {self.profile}'


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('ai', 'AI'),
    ]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self) -> str:
        return f'{self.role}: {self.content[:50]}...'


class MedicalRecord(models.Model):
    CATEGORY_CHOICES = [
        ('lab_reports', 'Lab Reports'),
        ('prescriptions', 'Prescriptions'),
        ('diagnoses', 'Diagnoses'),
        ('vitals', 'Vitals'),
        ('imaging', 'Imaging'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('normal', 'Normal'),
        ('attention', 'Needs Attention'),
        ('critical', 'Critical'),
    ]

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='medical_records')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    doctor = models.CharField(max_length=255, blank=True, default='')
    facility = models.CharField(max_length=255, blank=True, default='')
    record_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='normal')
    source_filename = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-record_date', '-created_at']

    def __str__(self) -> str:
        return f'{self.title} - {self.category}'


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('calling', 'Calling Hospital'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='appointments')
    hospital_name = models.CharField(max_length=255)
    hospital_address = models.CharField(max_length=500, blank=True)
    hospital_phone = models.CharField(max_length=20, blank=True)
    hospital_place_id = models.CharField(max_length=255, blank=True)
    
    # Appointment details (filled after AI call)
    appointment_date = models.DateField(null=True, blank=True)
    appointment_time = models.TimeField(null=True, blank=True)
    doctor_name = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255, blank=True)
    purpose = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    
    # Call tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    call_sid = models.CharField(max_length=100, blank=True)
    call_transcript = models.TextField(blank=True)
    call_duration = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.hospital_name} - {self.status}'

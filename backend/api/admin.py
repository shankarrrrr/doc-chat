from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('supabase_uid', 'email', 'full_name', 'onboarding_completed', 'updated_at')
    search_fields = ('supabase_uid', 'email', 'full_name')

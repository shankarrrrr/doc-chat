# Generated manually to add role field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_doctor_dashboard'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='role',
            field=models.CharField(
                max_length=20,
                choices=[('patient', 'Patient'), ('doctor', 'Doctor')],
                default='patient'
            ),
        ),
    ]

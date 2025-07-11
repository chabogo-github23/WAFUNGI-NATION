# Generated by Django 5.2.1 on 2025-07-07 17:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wafungi', '0002_alter_notification_options_notification_action_url_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='notification',
            options={},
        ),
        migrations.RenameField(
            model_name='eventapplication',
            old_name='application_message',
            new_name='cover_letter',
        ),
        migrations.RemoveField(
            model_name='eventapplication',
            name='reviewed_at',
        ),
        migrations.RemoveField(
            model_name='notification',
            name='action_url',
        ),
        migrations.RemoveField(
            model_name='notification',
            name='notification_type',
        ),
        migrations.RemoveField(
            model_name='notification',
            name='related_object_id',
        ),
        migrations.AddField(
            model_name='eventapplication',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='booking',
            name='event_application',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='booking', to='wafungi.eventapplication'),
        ),
        migrations.AlterField(
            model_name='eventapplication',
            name='proposed_rate',
            field=models.DecimalField(decimal_places=2, help_text='Your proposed rate for this event', max_digits=10),
        ),
        migrations.AlterField(
            model_name='eventapplication',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined'), ('withdrawn', 'Withdrawn')], default='pending', max_length=20),
        ),
    ]

# Generated by Django 5.0.2 on 2025-06-21 08:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0009_add_performance_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='duration',
            field=models.PositiveIntegerField(blank=True, help_text='動画の長さ（秒）', null=True),
        ),
    ]

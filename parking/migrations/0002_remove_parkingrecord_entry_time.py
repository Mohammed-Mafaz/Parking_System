# Generated by Django 5.0.4 on 2025-04-25 11:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('parking', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='parkingrecord',
            name='entry_time',
        ),
    ]

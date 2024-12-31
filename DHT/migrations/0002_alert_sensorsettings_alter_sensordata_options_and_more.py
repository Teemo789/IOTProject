# Generated by Django 5.1.3 on 2024-12-30 09:09

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('DHT', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Alert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('temperature', 'Temperature Alert'), ('humidity', 'Humidity Alert'), ('system', 'System Alert')], max_length=50)),
                ('message', models.TextField()),
                ('severity', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('resolved', models.BooleanField(default=False)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('resolution_notes', models.TextField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Alert',
                'verbose_name_plural': 'Alerts',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SensorSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('temperature_min_threshold', models.FloatField(default=10, validators=[django.core.validators.MinValueValidator(-40), django.core.validators.MaxValueValidator(80)])),
                ('temperature_max_threshold', models.FloatField(default=30, validators=[django.core.validators.MinValueValidator(-40), django.core.validators.MaxValueValidator(80)])),
                ('humidity_min_threshold', models.FloatField(default=30, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('humidity_max_threshold', models.FloatField(default=80, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('reading_interval', models.IntegerField(default=300, help_text='Interval between sensor readings in seconds')),
                ('alert_email', models.EmailField(blank=True, help_text='Email address for alert notifications', max_length=254, null=True)),
            ],
            options={
                'verbose_name': 'Sensor Settings',
                'verbose_name_plural': 'Sensor Settings',
            },
        ),
        migrations.AlterModelOptions(
            name='sensordata',
            options={'ordering': ['-date_recorded'], 'verbose_name': 'Sensor Data', 'verbose_name_plural': 'Sensor Data'},
        ),
        migrations.AddField(
            model_name='sensordata',
            name='is_verified',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='sensordata',
            name='notes',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='sensordata',
            name='date_recorded',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='sensordata',
            name='humidity',
            field=models.FloatField(validators=[django.core.validators.MinValueValidator(0, message='Humidity cannot be below 0%'), django.core.validators.MaxValueValidator(100, message='Humidity cannot exceed 100%')]),
        ),
        migrations.AlterField(
            model_name='sensordata',
            name='temperature',
            field=models.FloatField(validators=[django.core.validators.MinValueValidator(-40, message='Temperature cannot be below -40°C'), django.core.validators.MaxValueValidator(80, message='Temperature cannot exceed 80°C')]),
        ),
        migrations.AddIndex(
            model_name='sensordata',
            index=models.Index(fields=['temperature'], name='DHT_sensord_tempera_c0ea1e_idx'),
        ),
        migrations.AddIndex(
            model_name='sensordata',
            index=models.Index(fields=['humidity'], name='DHT_sensord_humidit_5e38ff_idx'),
        ),
        migrations.AddField(
            model_name='alert',
            name='related_data',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='alerts', to='DHT.sensordata'),
        ),
        migrations.AddIndex(
            model_name='alert',
            index=models.Index(fields=['type'], name='DHT_alert_type_841b77_idx'),
        ),
        migrations.AddIndex(
            model_name='alert',
            index=models.Index(fields=['severity'], name='DHT_alert_severit_ee3d74_idx'),
        ),
        migrations.AddIndex(
            model_name='alert',
            index=models.Index(fields=['resolved'], name='DHT_alert_resolve_ffa477_idx'),
        ),
    ]
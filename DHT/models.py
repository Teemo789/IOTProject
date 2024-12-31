from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
import statistics

class SensorData(models.Model):
    temperature = models.FloatField(
        validators=[
            MinValueValidator(-40, message="Temperature cannot be below -40°C"),
            MaxValueValidator(80, message="Temperature cannot exceed 80°C")
        ]
    )
    humidity = models.FloatField(
        validators=[
            MinValueValidator(0, message="Humidity cannot be below 0%"),
            MaxValueValidator(100, message="Humidity cannot exceed 100%")
        ]
    )
    date_recorded = models.DateTimeField(auto_now_add=True, db_index=True)
    is_verified = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=100, default='main-sensor')
    data_quality = models.CharField(
        max_length=20,
        choices=[
            ('high', 'High Quality'),
            ('medium', 'Medium Quality'),
            ('low', 'Low Quality'),
            ('error', 'Error')
        ],
        default='high'
    )
    battery_level = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Battery level of the sensor in percentage"
    )

    class Meta:
        ordering = ['-date_recorded']
        indexes = [
            models.Index(fields=['temperature']),
            models.Index(fields=['humidity']),
            models.Index(fields=['date_recorded', 'location']),
            models.Index(fields=['data_quality']),
        ]
        verbose_name = 'Sensor Data'
        verbose_name_plural = 'Sensor Data'

    def __str__(self):
        return f"Temp: {self.temperature}°C, Hum: {self.humidity}% - {self.date_recorded}"

    def is_data_fresh(self):
        return timezone.now() - self.date_recorded < timedelta(minutes=5)

    def get_status(self):
        status = {
            'temperature': 'normal',
            'humidity': 'normal',
            'warnings': [],
            'data_quality': self.data_quality,
            'freshness': 'fresh' if self.is_data_fresh() else 'stale'
        }

        settings = SensorSettings.get_settings()

        if self.temperature > settings.temperature_max_threshold:
            status['temperature'] = 'high'
            status['warnings'].append(f'High temperature detected: {self.temperature}°C')
        elif self.temperature < settings.temperature_min_threshold:
            status['temperature'] = 'low'
            status['warnings'].append(f'Low temperature detected: {self.temperature}°C')

        if self.humidity > settings.humidity_max_threshold:
            status['humidity'] = 'high'
            status['warnings'].append(f'High humidity detected: {self.humidity}%')
        elif self.humidity < settings.humidity_min_threshold:
            status['humidity'] = 'low'
            status['warnings'].append(f'Low humidity detected: {self.humidity}%')

        return status

    @classmethod
    def get_daily_statistics(cls, date):
        daily_data = cls.objects.filter(
            date_recorded__date=date,
            is_verified=True
        )

        if not daily_data.exists():
            return None

        temps = [d.temperature for d in daily_data]
        hums = [d.humidity for d in daily_data]

        return {
            'temperature': {
                'min': min(temps),
                'max': max(temps),
                'avg': statistics.mean(temps),
                'median': statistics.median(temps),
                'std_dev': statistics.stdev(temps) if len(temps) > 1 else 0
            },
            'humidity': {
                'min': min(hums),
                'max': max(hums),
                'avg': statistics.mean(hums),
                'median': statistics.median(hums),
                'std_dev': statistics.stdev(hums) if len(hums) > 1 else 0
            },
            'readings_count': len(temps),
            'quality_distribution': daily_data.values('data_quality').annotate(
                count=models.Count('id')
            )
        }

class Alert(models.Model):
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    TYPE_CHOICES = [
        ('temperature', 'Temperature Alert'),
        ('humidity', 'Humidity Alert'),
        ('system', 'System Alert'),
        ('battery', 'Battery Alert'),
        ('connection', 'Connection Alert'),
        ('data_quality', 'Data Quality Alert'),
    ]

    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True, null=True)
    related_data = models.ForeignKey(
        SensorData,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alerts'
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_alerts'
    )
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['type']),
            models.Index(fields=['severity']),
            models.Index(fields=['resolved']),
            models.Index(fields=['acknowledged']),
        ]
        verbose_name = 'Alert'
        verbose_name_plural = 'Alerts'

    def __str__(self):
        return f"{self.get_type_display()} - {self.severity} - {self.created_at}"

    def resolve(self, user=None, notes=None):
        self.resolved = True
        self.resolved_at = timezone.now()
        if notes:
            self.resolution_notes = notes
        if user:
            self.resolution_notes = f"{self.resolution_notes}\nResolved by: {user.username}"
        self.save()

    def acknowledge(self, user):
        self.acknowledged = True
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save()

    @property
    def resolution_time(self):
        if self.resolved and self.resolved_at:
            return self.resolved_at - self.created_at
        return None

class SensorSettings(models.Model):
    temperature_min_threshold = models.FloatField(
        default=10,
        validators=[MinValueValidator(-40), MaxValueValidator(80)]
    )
    temperature_max_threshold = models.FloatField(
        default=30,
        validators=[MinValueValidator(-40), MaxValueValidator(80)]
    )
    humidity_min_threshold = models.FloatField(
        default=30,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    humidity_max_threshold = models.FloatField(
        default=80,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    reading_interval = models.IntegerField(
        default=300,
        help_text="Interval between sensor readings in seconds"
    )
    alert_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email address for alert notifications"
    )
    alert_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Phone number for SMS alerts"
    )
    maintenance_mode = models.BooleanField(
        default=False,
        help_text="When enabled, certain alerts are suppressed"
    )
    data_retention_days = models.IntegerField(
        default=365,
        help_text="Number of days to retain sensor data"
    )
    critical_battery_threshold = models.IntegerField(
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Battery level threshold for alerts (%)"
    )

    class Meta:
        verbose_name = 'Sensor Settings'
        verbose_name_plural = 'Sensor Settings'

    def __str__(self):
        return "Sensor Settings"

    @classmethod
    def get_settings(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings

class DataLog(models.Model):
    EVENT_TYPES = [
        ('data_capture', 'Data Capture'),
        ('alert_generated', 'Alert Generated'),
        ('alert_resolved', 'Alert Resolved'),
        ('system_status', 'System Status'),
        ('maintenance', 'Maintenance'),
        ('error', 'Error'),
        ('warning', 'Warning'),
        ('info', 'Information'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    description = models.TextField()
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='data_logs'
    )
    related_data = models.ForeignKey(
        SensorData,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs'
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['event_type']),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.timestamp}"

class MaintenanceSchedule(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    scheduled_date = models.DateTimeField()
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_maintenances'
    )
    notes = models.TextField(blank=True, null=True)
    priority = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
        ],
        default='medium'
    )

    class Meta:
        ordering = ['-scheduled_date']
        indexes = [
            models.Index(fields=['scheduled_date']),
            models.Index(fields=['completed']),
        ]

    def __str__(self):
        return f"{self.title} - {self.scheduled_date}"

    def complete(self, user, notes=None):
        self.completed = True
        self.completed_at = timezone.now()
        self.completed_by = user
        if notes:
            self.notes = notes
        self.save()


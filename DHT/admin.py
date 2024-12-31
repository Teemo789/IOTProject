from django.contrib import admin
from .models import SensorData, Alert, SensorSettings

admin.site.register(SensorData)
admin.site.register(Alert)
admin.site.register(SensorSettings)
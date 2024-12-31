from django.urls import path
from . import views

urlpatterns = [
    # Data endpoints
    path('post/', views.post_data, name='post_data'),
    path('get_live_data/', views.get_live_data, name='get_live_data'),
    path('get_data_with_filters/', views.get_data_with_filters, name='get_data_with_filters'),
    path('get_statistics/', views.get_statistics, name='get_statistics'),
    path('get_alerts/', views.get_alerts, name='get_alerts'),

    # Enhanced endpoints
    path('past_days/<int:days>/', views.get_past_days_data, name='get_past_days_data'),
    path('date_average/', views.get_date_average, name='get_date_average'),
    path('temperature_trends/', views.get_temperature_trends, name='get_temperature_trends'),
    path('system_health/', views.get_system_health, name='get_system_health'),
    path('monthly_data/', views.get_monthly_data, name='get_monthly_data'),
    path('custom_interval/', views.get_custom_interval_data, name='get_custom_interval_data'),

    # Authentication endpoints
    path('register/', views.register_user, name='register_user'),
    path('login/', views.login_user, name='login_user'),
    path('logout/', views.logout_user, name='logout_user'),
]


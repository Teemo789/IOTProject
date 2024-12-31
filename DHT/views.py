import json
from datetime import datetime, timedelta
from django.db.models import Q, Avg, Max, Min, Count, F, ExpressionWrapper, fields
from django.db import models
from django.db.models.functions import TruncDate, TruncHour, ExtractHour, TruncMonth
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import SensorData, Alert, DataLog, SensorSettings
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from rest_framework import status

def check_and_create_alerts(temperature, humidity):
    settings = SensorSettings.get_settings()

    if temperature > settings.temperature_max_threshold:
        Alert.objects.create(
            type='temperature',
            message=f'High temperature detected: {temperature}°C',
            severity='high'
        )
    elif temperature < settings.temperature_min_threshold:
        Alert.objects.create(
            type='temperature',
            message=f'Low temperature detected: {temperature}°C',
            severity='medium'
        )

    if humidity > settings.humidity_max_threshold:
        Alert.objects.create(
            type='humidity',
            message=f'High humidity detected: {humidity}%',
            severity='medium'
        )
    elif humidity < settings.humidity_min_threshold:
        Alert.objects.create(
            type='humidity',
            message=f'Low humidity detected: {humidity}%',
            severity='medium'
        )

@api_view(['POST'])
def post_data(request):
    try:
        # Print the raw data for debugging
        print("Received data:", request.data)

        # Try to get temperature and humidity from the request data
        temperature = request.data.get('temp')
        humidity = request.data.get('hum')

        # If temp and hum are not in request.data, try to parse the body as JSON
        if temperature is None or humidity is None:
            try:
                json_data = json.loads(request.body)
                temperature = json_data.get('temp')
                humidity = json_data.get('hum')
            except json.JSONDecodeError:
                return Response({'error': 'Invalid JSON data'}, status=400)

        if temperature is None or humidity is None:
            return Response({'error': 'Temperature or humidity data missing!'}, status=400)

        try:
            temperature = float(temperature)
            humidity = float(humidity)
        except ValueError:
            return Response({'error': 'Temperature and humidity must be valid numbers!'}, status=400)

        if temperature < -40 or temperature > 80:
            return Response({'error': 'Temperature out of valid range (-40°C to 80°C)'}, status=400)
        if humidity < 0 or humidity > 100:
            return Response({'error': 'Humidity out of valid range (0% to 100%)'}, status=400)

        sensor_data = SensorData(temperature=temperature, humidity=humidity)
        sensor_data.save()

        DataLog.objects.create(
            event_type="data_capture",
            description=f"Temperature: {temperature}°C, Humidity: {humidity}%"
        )

        check_and_create_alerts(temperature, humidity)

        return Response({'message': 'Data received and saved successfully!'}, status=201)
    except Exception as e:
        print(f"Error in post_data: {str(e)}")
        return Response({'error': f'Something went wrong: {str(e)}'}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_live_data(request):
    try:
        latest_data = SensorData.objects.last()
        if not latest_data:
            return Response({'error': 'No data available'}, status=404)

        time_difference = timezone.now() - latest_data.date_recorded
        minutes_ago = time_difference.total_seconds() / 60

        previous_data = SensorData.objects.filter(
            date_recorded__lt=latest_data.date_recorded
        ).order_by('-date_recorded').first()

        response_data = {
            'temp': latest_data.temperature,
            'hum': latest_data.humidity,
            'date': latest_data.date_recorded,
            'capture_info': {
                'minutes_ago': round(minutes_ago, 1),
                'timestamp': latest_data.date_recorded.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'STALE' if minutes_ago > 5 else 'FRESH'
            }
        }

        if previous_data:
            response_data['changes'] = {
                'temp_change': round(latest_data.temperature - previous_data.temperature, 2),
                'hum_change': round(latest_data.humidity - previous_data.humidity, 2)
            }

        if minutes_ago > 5:
            response_data['warning'] = 'Data may be stale. Last update was more than 5 minutes ago.'

        return Response(response_data)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_data_with_filters(request):
    try:
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        min_temp = request.query_params.get('min_temp')
        max_temp = request.query_params.get('max_temp')
        min_humidity = request.query_params.get('min_humidity')
        max_humidity = request.query_params.get('max_humidity')

        queryset = SensorData.objects.all()

        if start_date:
            queryset = queryset.filter(date_recorded__gte=start_date)
        if end_date:
            queryset = queryset.filter(date_recorded__lte=end_date)
        if min_temp:
            queryset = queryset.filter(temperature__gte=float(min_temp))
        if max_temp:
            queryset = queryset.filter(temperature__lte=float(max_temp))
        if min_humidity:
            queryset = queryset.filter(humidity__gte=float(min_humidity))
        if max_humidity:
            queryset = queryset.filter(humidity__lte=float(max_humidity))

        queryset = queryset.order_by('-date_recorded')

        data = [{
            'id': item.id,
            'temperature': item.temperature,
            'humidity': item.humidity,
            'date_recorded': item.date_recorded,
            'location': item.location,
            'data_quality': item.data_quality
        } for item in queryset]

        return Response({
            'count': len(data),
            'data': data
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_statistics(request):
    try:
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        queryset = SensorData.objects.all()

        if start_date:
            queryset = queryset.filter(date_recorded__gte=start_date)
        if end_date:
            queryset = queryset.filter(date_recorded__lte=end_date)

        stats = queryset.aggregate(
            avg_temp=Avg('temperature'),
            max_temp=Max('temperature'),
            min_temp=Min('temperature'),
            avg_hum=Avg('humidity'),
            max_hum=Max('humidity'),
            min_hum=Min('humidity'),
            count=Count('id')
        )

        return Response(stats)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_alerts(request):
    try:
        alerts = Alert.objects.all().order_by('-created_at')
        data = [{
            'id': alert.id,
            'type': alert.type,
            'message': alert.message,
            'severity': alert.severity,
            'created_at': alert.created_at,
            'resolved': alert.resolved
        } for alert in alerts]

        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_past_days_data(request, days):
    try:
        if days not in [7, 30]:
            return Response({'error': 'Only 7 or 30 days periods are supported'}, status=400)

        start_date = timezone.now() - timedelta(days=days)

        daily_data = SensorData.objects.filter(
            date_recorded__gte=start_date
        ).annotate(
            date=TruncDate('date_recorded')
        ).values('date').annotate(
            avg_temp=Avg('temperature'),
            avg_hum=Avg('humidity'),
            max_temp=Max('temperature'),
            min_temp=Min('temperature'),
            max_hum=Max('humidity'),
            min_hum=Min('humidity'),
            readings_count=Count('id')
        ).order_by('date')

        data_list = list(daily_data)
        for i in range(len(data_list)):
            if i > 0:
                data_list[i]['temp_change'] = data_list[i]['avg_temp'] - data_list[i - 1]['avg_temp']
            else:
                data_list[i]['temp_change'] = 0

        return Response({
            'period': f'Past {days} days',
            'data': data_list,
            'summary': {
                'avg_temp': sum(d['avg_temp'] for d in data_list) / len(data_list),
                'avg_hum': sum(d['avg_hum'] for d in data_list) / len(data_list),
                'total_readings': sum(d['readings_count'] for d in data_list)
            }
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_date_average(request):
    try:
        date_str = request.query_params.get('date')
        if not date_str:
            return Response({'error': 'Date parameter is required (YYYY-MM-DD)'}, status=400)

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

        data = SensorData.objects.filter(
            date_recorded__date=target_date
        ).aggregate(
            avg_temp=Avg('temperature'),
            avg_hum=Avg('humidity'),
            max_temp=Max('temperature'),
            min_temp=Min('temperature'),
            reading_count=Count('id'),
            morning_avg_temp=Avg('temperature', filter=Q(date_recorded__hour__lt=12)),
            afternoon_avg_temp=Avg('temperature', filter=Q(date_recorded__hour__gte=12))
        )

        if data['avg_temp'] is None:
            return Response({
                'message': f'No data captured for date {date_str}',
                'status': 'NO_DATA'
            })

        return Response({
            'date': date_str,
            'statistics': data,
            'day_period_comparison': {
                'morning_average': data['morning_avg_temp'],
                'afternoon_average': data['afternoon_avg_temp']
            }
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_temperature_trends(request):
    try:
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)

        hourly_trends = SensorData.objects.filter(
            date_recorded__gte=start_date
        ).annotate(
            hour=ExtractHour('date_recorded')
        ).values('hour').annotate(
            avg_temp=Avg('temperature'),
            avg_hum=Avg('humidity'),
            sample_count=Count('id')
        ).order_by('hour')

        sorted_by_temp = sorted(hourly_trends, key=lambda x: x['avg_temp'], reverse=True)
        hottest_hours = sorted_by_temp[:3]
        coolest_hours = sorted_by_temp[-3:]

        return Response({
            'hourly_trends': list(hourly_trends),
            'peak_hours': {
                'hottest_hours': hottest_hours,
                'coolest_hours': coolest_hours
            },
            'period': f'Past {days} days'
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_system_health(request):
    try:
        now = timezone.now()
        last_hour = now - timedelta(hours=1)

        metrics = {
            'data_collection': {
                'last_hour_readings': SensorData.objects.filter(
                    date_recorded__gte=last_hour
                ).count(),
                'total_readings': SensorData.objects.count(),
                'last_reading': SensorData.objects.last().date_recorded if SensorData.objects.exists() else None
            },
            'alerts': {
                'active_alerts': Alert.objects.filter(
                    created_at__gte=last_hour
                ).count(),
                'alert_distribution': Alert.objects.filter(
                    created_at__gte=now - timedelta(days=1)
                ).values('severity').annotate(count=Count('id'))
            },
            'system_status': {
                'last_error': Alert.objects.filter(
                    severity='high'
                ).order_by('-created_at').first(),
                'data_capture_rate': DataLog.objects.filter(
                    timestamp__gte=last_hour
                ).count()
            }
        }

        return Response(metrics)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_monthly_data(request):
    try:
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        monthly_data = SensorData.objects.filter(
            date_recorded__gte=current_month
        ).annotate(
            day=TruncDate('date_recorded')
        ).values('day').annotate(
            avg_temp=Avg('temperature'),
            avg_hum=Avg('humidity'),
            max_temp=Max('temperature'),
            min_temp=Min('temperature'),
            max_hum=Max('humidity'),
            min_hum=Min('humidity'),
            readings_count=Count('id')
        ).order_by('day')

        return Response({
            'period': f'Current month ({current_month.strftime("%B %Y")})',
            'data': list(monthly_data)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_custom_interval_data(request):
    try:
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date or not end_date:
            return Response({'error': 'Both start_date and end_date are required'}, status=400)

        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

        if start_date > end_date:
            return Response({'error': 'start_date must be before end_date'}, status=400)

        interval_data = SensorData.objects.filter(
            date_recorded__date__gte=start_date,
            date_recorded__date__lte=end_date
        ).annotate(
            day=TruncDate('date_recorded')
        ).values('day').annotate(
            avg_temp=Avg('temperature'),
            avg_hum=Avg('humidity'),
            max_temp=Max('temperature'),
            min_temp=Min('temperature'),
            max_hum=Max('humidity'),
            min_hum=Min('humidity'),
            readings_count=Count('id')
        ).order_by('day')

        return Response({
            'period': f'From {start_date} to {end_date}',
            'data': list(interval_data)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['POST'])
def register_user(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email')

    if not username or not password or not email:
        return Response({'error': 'Username, password, and email are required'}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=400)

    user = User.objects.create_user(username=username, email=email, password=password)
    return Response({'message': 'User registered successfully'}, status=201)

@api_view(['POST'])
def login_user(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({'error': 'Username and password are required'}, status=400)

    user = User.objects.filter(username=username).first()

    if user is None or not user.check_password(password):
        return Response({'error': 'Invalid credentials'}, status=400)

    refresh = RefreshToken.for_user(user)
    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    try:
        refresh_token = request.data.get('refresh_token')
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'User logged out successfully'}, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


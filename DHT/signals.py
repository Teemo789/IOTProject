from venv import logger

from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group

@receiver(post_migrate)
def create_roles(sender, **kwargs):
    try:
        Group.objects.get_or_create(name='admin')
        Group.objects.get_or_create(name='employe')
        logger.info('Roles created successfully')
    except Exception as e:
        logger.error(f"Error creating roles: {e}")


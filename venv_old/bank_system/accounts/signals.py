from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import UserProfile
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, BankAccount

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

# accounts/signals.py


@receiver(post_save, sender=User)
def create_user_account(sender, instance, created, **kwargs):
    if created:
        # BankAccount save() will generate a unique account number
        BankAccount.objects.create(user=instance)

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
import random

# ✅ Custom User Model
class User(AbstractUser):
    is_customer = models.BooleanField(default=True)

    def __str__(self):
        return self.username

# ✅ Bank Account Model (Only once, fully updated)
class BankAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=20, unique=True, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    profile_image = models.ImageField(upload_to='profile_images/', default='profile_images/default.png')

    def __str__(self):
        return f"{self.user.username} - {self.account_number}"

    def save(self, *args, **kwargs):
        if not self.account_number:
            self.account_number = self.generate_account_number()
        super().save(*args, **kwargs)

    def generate_account_number(self):
        while True:
            number = str(random.randint(10**11, 10**12 - 1))  # 12-digit number
            if not BankAccount.objects.filter(account_number=number).exists():
                return number

# ✅ Transaction Model
class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('withdraw', 'Withdraw'),
        ('transfer', 'Transfer'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - Rs. {self.amount}"

# ✅ User Profile Model
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='profile_pics/', default='default.jpg')

    def __str__(self):
        return self.user.username


from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone




class Employee(AbstractUser):
    email = models.EmailField(blank=True, null=True, unique=False)
    phone = models.CharField(max_length=50, blank=True)
    joined_at = models.DateField(default=timezone.now)


    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    @property
    def initials(self) -> str:
        initials = (self.first_name[:1] + self.last_name[:1]).upper()
        return initials if initials.strip() else self.username[:2].upper()

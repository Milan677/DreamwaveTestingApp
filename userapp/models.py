
from django.db import models
from django.contrib.auth.models import AbstractBaseUser,BaseUserManager,PermissionsMixin
from django.utils.timezone import now,timedelta
from django.utils.crypto import get_random_string
import random

# Create your models here.
class CustomUserManager(BaseUserManager):
    def create_user(self,email,mobile_no,username=None,password=None,**extra_fields):
        if not email:
            raise ValueError("Email is required")
        if not mobile_no:
            raise ValueError("Mobile number is required")
        
        
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            mobile_no=mobile_no,
            username=username if username else '',
            **extra_fields
        )
        user.set_password(password)
        user.save(using = self._db)

        return user
 

class CustomUser(AbstractBaseUser,PermissionsMixin):
    username = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    mobile_no = models.CharField(max_length=15)
    otp = models.CharField(max_length=10,null=True,blank=True)
    last_login = models.DateTimeField(default=now,blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    reset_token = models.CharField(max_length=255, blank=True, null=True)
    reset_token_expiry = models.DateTimeField(blank=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['mobile_no']
    
    def generate_otp(self):
        self.otp = str(random.randint(100000,999999))
        self.save()

    def generate_reset_token(self):
        self.reset_token = get_random_string(50)
        self.reset_token_expiry = now() + timedelta(hours=1)
        self.save()            

    def __str__(self):
        return self.email  
from django.urls import path,include
from .views import *

urlpatterns = [
    path('register/', register_user, name='user-register'),
    path('login/request-otp/',requestOtp,name="request-otp"),
    path('login/verify-otp/',verifyOtp,name="verify-otp"),
    path('logout/',Logout_user,name="logout-user"),
    path('test/',protected_view),
]
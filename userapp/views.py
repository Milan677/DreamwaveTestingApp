

# Create your views here.
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes,authentication_classes
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken,AccessToken
from django.contrib.auth.hashers import make_password,check_password
from .serializers import *
from .models import *
import uuid
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([AllowAny])
def register_user(request):
    try:
        serializer = CustomUserSerializers(data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message":"Registraion Successfull !"},status=status.HTTP_200_OK)

        return Response(serializer.errors,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        return Response({
            "error": str(e),
            "message": "Error occurred in registraion view"
        },status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([AllowAny])
def requestOtp(request):
    try:
        email = request.data.get('email')
        user = CustomUser.objects.filter(email=email).first()
        print("===========")
        print(user)
        if user:
            user.generate_otp()

            #sent email
            send_mail(
                "Your OTP",
                f"Your OTP is : {user.otp}",
                settings.EMAIL_HOST_USER,
                [user.email]
            )

            return Response({"message":"Otp sent"},status=status.HTTP_200_OK)
        
        return Response({"error":"user not found !"},status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            "error": str(e),
            "message": "Error occurred in otp send view"
        },status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([AllowAny])
def verifyOtp(request):
    try:
        email = request.data.get('email')
        otp = request.data.get('otp')

        if not email or not otp:
            return Response({"message":"valid email or otp required !"})
        
        user = CustomUser.objects.filter(email=email,otp=otp).first()
        if user:
            refresh = RefreshToken.for_user(user)
            user.otp =  None
            user.save()

            return Response({
                "message":"Login successfull",
                "access_token":str(refresh.access_token),
                "refresh_token":str(refresh),
                "user_details":{
                    "name":user.username,
                    "email":user.email,
                }
            })
        return Response({"error":"Invalid OTP"},status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        return Response({
            "error": str(e),
            "message": "Error occurred in verify otp view"
        },status=status.HTTP_500_INTERNAL_SERVER_ERROR)    
    

@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes(IsAuthenticated)
def Logout_user(request):
    try:
        refresh_token = request.data.get('refresh_token')
        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response({"message":"Logout successfully !"},status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            "error": str(e),
            "message": "Error occurred in logout view"
        },status=status.HTTP_500_INTERNAL_SERVER_ERROR)    
    

@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def protected_view(request):
    data = request.user
    return Response(request.user.email)    
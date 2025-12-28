
from .serializers import StepLogSerializer
from django.db.models import Sum
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import StepLog
#JWT ko lagi
from rest_framework import generics
from django.contrib.auth.models import User
from .serializers import UserSerializer
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class StepLogUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = StepLogSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class StepLogAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        period = request.query_params.get('period', 'daily')

        # Clean query without citation text
        queryset = StepLog.objects.filter(user=user)

        if period == 'weekly':
            data = (
                queryset.annotate(period_label=TruncWeek('date'))
                .values('period_label')
                .annotate(total_steps=Sum('step_count'))
                .order_by('-period_label')
            )
        elif period == 'monthly':
            data = (
                queryset.annotate(period_label=TruncMonth('date'))
                .values('period_label')
                .annotate(total_steps=Sum('step_count'))
                .order_by('-period_label')
            )
        else:
            # Daily (individual entries)
            data = queryset.values('date', 'step_count').order_by('-date')

        return Response({
            "period": period,
            "results": list(data)
        }, status=status.HTTP_200_OK)
#login
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    permission_classes = [AllowAny]
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token['username'] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user_id'] = self.user.id
        data['username'] = self.user.username
        data['email'] = self.user.email
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer

# rep_rise/views.py

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist() # Adds the token to the database blacklist

            return Response({"detail": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": "Invalid token or already logged out."}, status=status.HTTP_400_BAD_REQUEST)
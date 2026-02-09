from datetime import timezone
import calendar
from datetime import date
from datetime import timedelta
from datetime import datetime

from .ml_logic import generate_workout_plan
from .serializers import StepLogSerializer, ProfileSerializer, \
    CustomTokenObtainPairSerializer, WorkoutRecommendationSerializer
from django.utils import timezone

from .models import Profile, WorkoutRecommendation
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import StepLog
from rest_framework import generics
from django.contrib.auth.models import User
from .serializers import UserSerializer
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken






#login

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()


        refresh = RefreshToken.for_user(user)

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
        }, status=status.HTTP_201_CREATED)


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


class UsernameCheckView(APIView):

    permission_classes = [AllowAny]

    def get(self, request):
        username = request.query_params.get('username', None)

        if not username:
            return Response(
                {"error": "Username parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )


        is_taken = User.objects.filter(username__exact=username).exists()

        return Response({
            "username": username,
            "is_taken": is_taken,
            "available": not is_taken,
            "message": "Username is taken." if is_taken else "Username is available."
        }, status=status.HTTP_200_OK)


class ProfileManageView(generics.RetrieveUpdateAPIView):

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        # This get_or_create logic fixes the "RelatedObjectDoesNotExist" error
        # by creating a default profile if one is missing.
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        return profile



#For Steps Related

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
        target_date_str = request.query_params.get('date')

        if target_date_str:
            try:
                anchor_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid date format."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            anchor_date = timezone.now().date()

        # Simplify goal logic: Just use the profile goal
        goal = user.profile.daily_step_goal if hasattr(user, 'profile') else 10000

        if period == 'daily':
            log = StepLog.objects.filter(user=user, date=anchor_date).first()
            data = {
                "date": anchor_date,
                "day_name": anchor_date.strftime('%a'),
                "steps": log.step_count if log else 0,
                "goal": goal,
                "calories_burned": log.calories_burned if log else 0,
                "distance_meters": log.distance_meters if log else 0,
                "duration_minutes": log.duration_minutes if log else 0
            }
            return Response(data)

        elif period == 'weekly':
            days_since_sunday = (anchor_date.weekday() + 1) % 7
            start_date = anchor_date - timedelta(days=days_since_sunday)
            end_date = anchor_date - timedelta(days=1)

            weekly_data = []
            current_check_date = start_date
            while current_check_date <= end_date:
                log = StepLog.objects.filter(user=user, date=current_check_date).first()
                weekly_data.append({
                    "date": current_check_date,
                    "day_name": current_check_date.strftime("%a"),
                    "steps": log.step_count if log else 0,
                    "goal": goal,
                })
                current_check_date += timedelta(days=1)
            return Response(weekly_data)

        elif period == 'monthly':
            today = timezone.now().date()
            year = int(request.query_params.get('year', today.year))
            month = int(request.query_params.get('month', today.month))

            _, num_days = calendar.monthrange(year, month)
            start_date = date(year, month, 1)
            end_date = date(year, month, num_days)

            total_steps = StepLog.objects.filter(
                user=user, date__range=[start_date, end_date]
            ).aggregate(total=Sum('step_count'))['total'] or 0

            # Total goal is just the daily goal * number of days in month
            total_goal = goal * num_days

            return Response({
                "total_steps": total_steps,
                "total_goal": total_goal,
                "avg_goal": goal
            })
## get profile ##
class CurrentUserView(generics.RetrieveAPIView):

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):

        Profile.objects.get_or_create(user=self.request.user)
        return self.request.user


class WorkoutRecommendationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # 1. Ensure Profile Exists
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return Response(
                {"error": "Profile not found. Please complete your profile first."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. Validation: Check if critical fields for ML are present
        if not all([profile.age, profile.height, profile.weight, profile.target_weight]):
             return Response(
                {"error": "Profile incomplete. Please update age, height, weight, and target weight."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Get or Create Recommendation Object
        rec, created = WorkoutRecommendation.objects.get_or_create(profile=profile)

        # 4. Generate Plan (Fallback/First-Time Logic)
        # Note: Regular updates are handled by ProfileSerializer.update(),
        # this block runs only if it's the first time or data is missing.
        if created or not rec.data:
            result = generate_workout_plan(
                age=profile.age,
                height=profile.height,
                weight=profile.weight,
                ideal_weight=profile.target_weight,
                fitness_level=profile.fitness_level
            )

            if result['status'] == 'error':
                 return Response(
                     {"error": f"Generation failed: {result.get('message')}"},
                     status=status.HTTP_500_INTERNAL_SERVER_ERROR
                 )

            # Save the new plan
            rec.data = result['schedule']
            rec.saved_weight = profile.weight
            # Save the meta-data returned by logic (it might have auto-calculated these)
            rec.saved_goal = result['meta']['goal']
            rec.saved_level = result['meta']['fitness_level']
            rec.save()

        # 5. Serialize and Return
        serializer = WorkoutRecommendationSerializer(rec)
        return Response(serializer.data, status=status.HTTP_200_OK)
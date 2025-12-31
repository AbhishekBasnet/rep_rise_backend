from datetime import timezone
import calendar
from datetime import date
from datetime import timedelta
from datetime import datetime


from .serializers import StepLogSerializer, StepGoalOverrideSerializer, StepGoalPlanSerializer, ProfileSerializer
from django.utils import timezone

from .models import Profile, StepGoalOverride, StepGoalPlan
from django.db.models import Sum
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
from rest_framework_simplejwt.tokens import RefreshToken






#login
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
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


class ProfileManageView(generics.RetrieveUpdateAPIView):
    """
    Get or Update the current user's profile.
    If the profile doesn't exist, it creates one automatically.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        # This get_or_create logic fixes the "RelatedObjectDoesNotExist" error
        # by creating a default profile if one is missing.
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        return profile

#For Steps Related

class StepGoalPlanRangeCreateView(generics.CreateAPIView):
    serializer_class = StepGoalPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

class StepLogUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = StepLogSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class StepGoalOverrideSingleView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = StepGoalOverrideSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StepLogAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_goal_for_date(self, user, target_date):
        """
        Priority Logic:
        1. Check StepGoalOverride (Single Day Exception) - HIGHEST PRIORITY
        2. Check StepGoalPlan (Date Range)
        3. Fallback to Profile.daily_step_goal (Default)
        """
        # 1. Check for specific day override
        override = StepGoalOverride.objects.filter(user=user, date=target_date).first()
        if override:
            return override.target_steps

        # 2. Check for range plan
        plan = StepGoalPlan.objects.filter(
            user=user,
            start_date__lte=target_date,
            end_date__gte=target_date
        ).first()
        if plan:
            return plan.target_steps

        # 3. Default
        return user.profile.daily_step_goal

    def get(self, request):
        user = request.user
        period = request.query_params.get('period', 'daily')

        # 1. READ THE DATE PARAMETER (Default to today if missing)
        target_date_str = request.query_params.get('date')
        if target_date_str:
            try:
                # Parse "2025-12-31" string into a Date object
                anchor_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            anchor_date = timezone.now().date()

        # --- DAILY ---
        if period == 'daily':
            goal = self.get_goal_for_date(user, anchor_date)
            log = StepLog.objects.filter(user=user, date=anchor_date).first()
            steps = log.step_count if log else 0

            return Response({
                "date": anchor_date,
                "steps": steps,
                "goal": goal,
                "remaining": max(0, goal - steps)
            })

        # --- WEEKLY ---
        elif period == 'weekly':
            days = 7
            # Calculate start date based on the requested anchor_date (End Date)
            # Example: If anchor is Sunday (22nd), start is Monday (16th)
            start_date = anchor_date - timedelta(days=days - 1)

            weekly_data = []

            for i in range(days):
                check_date = start_date + timedelta(days=i)
                daily_goal = self.get_goal_for_date(user, check_date)

                log = StepLog.objects.filter(user=user, date=check_date).first()
                daily_steps = log.step_count if log else 0

                weekly_data.append({
                    "date": check_date,
                    # Short day name for UI (e.g., "Mon", "Tue")
                    "day_name": check_date.strftime("%a"),
                    "steps": daily_steps,
                    "goal_per_day": daily_goal,
                    "remaining": max(0, daily_goal - daily_steps)
                })

            return Response(weekly_data)

        # --- MONTHLY ---
        elif period == 'monthly':
            # FIX: Get the current date again so we can use it as a default
            today = timezone.now().date()

            # 1. Determine the specific Year and Month to view
            try:
                year = int(request.query_params.get('year', today.year))
                month = int(request.query_params.get('month', today.month))
            except ValueError:
                return Response({"error": "Invalid year/month"}, status=status.HTTP_400_BAD_REQUEST)

            # 2. Calculate Start and End Date for that specific month
            _, num_days = calendar.monthrange(year, month)
            start_date = date(year, month, 1)
            end_date = date(year, month, num_days)

            # 3. Calculate Total Goal
            total_goal = 0
            for i in range(num_days):
                check_date = start_date + timedelta(days=i)
                total_goal += self.get_goal_for_date(user, check_date)

            # 4. Calculate Total Steps
            total_steps = StepLog.objects.filter(
                user=user,
                date__range=[start_date, end_date]
            ).aggregate(total=Sum('step_count'))['total'] or 0

            return Response({
                "period": "monthly",
                "total_steps": total_steps,
                "total_goal": total_goal,
                "avg_goal": total_goal // num_days
            })



class StepGoalPlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StepGoalPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):

        return StepGoalPlan.objects.filter(user=self.request.user)

# views.py

class StepGoalConsolidatedListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # 1. Get Params (Default to current month if not provided)
        now = timezone.now()
        try:
            year = int(request.query_params.get('year', now.year))
            month = int(request.query_params.get('month', now.month))
        except ValueError:
            return Response({"error": "Invalid year or month format"}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Calculate the date range for that specific month
        # calendar.monthrange returns (weekday, last_day_of_month)
        _, last_day = calendar.monthrange(year, month)
        month_start = date(year, month, 1)
        month_end = date(year, month, last_day)

        # 3. Filter Single Overrides
        # Simply check if the date falls in the requested month/year
        single_overrides = StepGoalOverride.objects.filter(
            user=user,
            date__year=year,
            date__month=month
        )
        single_serializer = StepGoalOverrideSerializer(single_overrides, many=True)

        # 4. Filter Ranged Goals (Overlap Logic)
        # We want any plan that *touches* this month.
        # Logic: Plan Start must be before Month End AND Plan End must be after Month Start.
        ranged_plans = StepGoalPlan.objects.filter(
            user=user,
            start_date__lte=month_end,
            end_date__gte=month_start
        )
        range_serializer = StepGoalPlanSerializer(ranged_plans, many=True)

        return Response({
            "year": year,
            "month": month,
            "single_overrides": single_serializer.data,
            "ranged_goals": range_serializer.data
        }, status=status.HTTP_200_OK)
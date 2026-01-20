from datetime import timezone
import calendar
from datetime import date
from datetime import timedelta
from datetime import datetime


from .serializers import StepLogSerializer, StepGoalOverrideSerializer, StepGoalPlanSerializer, ProfileSerializer, \
    CustomTokenObtainPairSerializer
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
            # fetch specific log for the anchor date (not just today)
            step_log = StepLog.objects.filter(user=user, date=anchor_date).first()

            # Determine Goal (Profile default or specific override if you have that logic)
            goal = 10000
            if hasattr(user, 'profile') and user.profile.daily_step_goal:
                goal = user.profile.daily_step_goal

            if step_log:
                data = {
                    "date": anchor_date,
                    "day_name": anchor_date.strftime('%a'),
                    "steps": step_log.step_count,
                    "goal": goal,
                    # Safe access to instance attributes
                    "calories_burned": step_log.calories_burned,
                    "distance_meters": step_log.distance_meters,
                    "duration_minutes": step_log.duration_minutes
                }
            else:
                # Zero state for past/future dates with no logs
                data = {
                    "date": anchor_date,
                    "day_name": anchor_date.strftime('%a'),
                    "steps": 0,
                    "goal": goal,
                    "calories_burned": 0,
                    "distance_meters": 0,
                    "duration_minutes": 0
                }

            return Response(data)


       # --- WEEKLY (Modified) ---
        elif period == 'weekly':
            # 1. Find the start of the current week (Sunday)
            # Python's weekday(): Mon=0 ... Sun=6
            # We want to subtract enough days to get back to Sunday.
            # If Today is Sun(6) -> (6+1)%7 = 0 days back.
            # If Today is Tue(1) -> (1+1)%7 = 2 days back (Sun, Mon).
            days_since_sunday = (anchor_date.weekday() + 1) % 7
            start_date = anchor_date - timedelta(days=days_since_sunday)
            
            # 2. End date is Yesterday (Exclude today per requirements)
            end_date = anchor_date - timedelta(days=1)

            weekly_data = []

            # 3. Iterate from Sunday up to Yesterday
            # If today is Sunday, start_date (Sun) > end_date (Sat), loop won't run -> Returns []
            current_check_date = start_date
            while current_check_date <= end_date:
                daily_goal = self.get_goal_for_date(user, current_check_date)
                log = StepLog.objects.filter(user=user, date=current_check_date).first()
                daily_steps = log.step_count if log else 0

                weekly_data.append({
                    "date": current_check_date,
                    "day_name": current_check_date.strftime("%a"),
                    "steps": daily_steps,
                    "goal": daily_goal,
                })
                
                current_check_date += timedelta(days=1)

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

## get profile ##
class CurrentUserView(generics.RetrieveAPIView):

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):

        Profile.objects.get_or_create(user=self.request.user)
        return self.request.user
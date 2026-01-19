from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import StepLog, Profile, StepGoalOverride, StepGoalPlan
from django.contrib.auth.models import User


#For User/Profiles
class ProfileSerializer(serializers.ModelSerializer):
    bmi = serializers.ReadOnlyField()

    class Meta:
        model = Profile
        fields = [
            'height', 'weight', 'age', 'gender',
            'daily_step_goal', 'bmi'
        ]

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    # Nested profile serializer to include goal and physical stats in user responses
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'profile']

    def create(self, validated_data):
        # standard user creation
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        # Ensure a Profile instance exists for the new user
        Profile.objects.get_or_create(user=user)
        return user

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

#For Steps Related

class StepGoalPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = StepGoalPlan
        fields = ['id', 'start_date', 'end_date', 'target_steps', 'description']

    def validate(self, data):
        user = self.context['request'].user
        start = data.get('start_date')
        end = data.get('end_date')

        # Basic date check
        if start and end and start > end:
            raise serializers.ValidationError("Start date cannot be after end date.")

        # Overlap Check
        if start and end:
            # Find any EXISTING plans that overlap
            overlap_query = StepGoalPlan.objects.filter(
                user=user,
                start_date__lte=end,
                end_date__gte=start
            )

            # CRITICAL FIX: If we are updating (self.instance exists),
            # exclude the current plan from the check so it doesn't block itself.
            if self.instance:
                overlap_query = overlap_query.exclude(pk=self.instance.pk)

            if overlap_query.exists():
                raise serializers.ValidationError("This date range overlaps with an existing goal plan.")

        return data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
class StepGoalOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model = StepGoalOverride
        fields = ['date', 'target_steps']

    def create(self, validated_data):
        user = self.context['request'].user
        # Logic: If an override for this date exists, update it; otherwise, create it.
        override, created = StepGoalOverride.objects.update_or_create(
            user=user,
            date=validated_data['date'],
            defaults={'target_steps': validated_data['target_steps']}
        )
        return override

class StepLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = StepLog
        fields = ['date', 'step_count']

    def create(self, validated_data):

        user = self.context['request'].user
        date = validated_data['date']
        step_count = validated_data['step_count']

        # 2. THE SELF-HEALING LOGIC
        # Check if multiple entries exist BEFORE trying to update
        existing_logs = StepLog.objects.filter(user=user, date=date)

        if existing_logs.count() > 1:
            print(
                f"⚠️ DANGER: Found {existing_logs.count()} duplicates for User {user.id} on {date}. Fixing now...")
            # Keep the most recent one (highest ID), delete the rest
            last_log = existing_logs.order_by('-id').first()
            existing_logs.exclude(id=last_log.id).delete()
            print("✅ Duplicates deleted. Proceeding.")

            # 3. Now it is 100% safe to call update_or_create
        step_log, created = StepLog.objects.update_or_create(
            user=user,
            date=date,
            defaults={'step_count': step_count}
        )
        return step_log
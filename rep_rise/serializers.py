from rest_framework import serializers
from .models import StepLog, Profile, StepGoalOverride, StepGoalPlan
from django.contrib.auth.models import User


#For User/Profiles
class ProfileSerializer(serializers.ModelSerializer):
    bmi = serializers.ReadOnlyField()  # Calculated via property in models.py

    class Meta:
        model = Profile
        fields = [
            'height', 'weight', 'birth_date',
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
        # Extract user from the request context provided by the view
        user = self.context['request'].user
        date = validated_data.get('date')
        step_count = validated_data.get('step_count')

        # Use update_or_create to handle the unique_together constraint
        step_log, created = StepLog.objects.update_or_create(
            user=user,
            date=date,
            defaults={'step_count': step_count}
        )
        return step_log
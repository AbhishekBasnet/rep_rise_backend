from rest_framework import serializers
from .models import StepLog
from django.contrib.auth.models import User
from .models import Profile

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

class ProfileSerializer(serializers.ModelSerializer):
    bmi = serializers.ReadOnlyField()

    class Meta:
        model = Profile
        fields = ['height', 'weight', 'birth_date', 'activity_level', 'fitness_goal', 'bmi']

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile']

    def create(self, validated_data):
        profile_data = validated_data.pop('profile')
        user = User.objects.create_user(**validated_data)
        Profile.objects.create(user=user, **profile_data)
        return user
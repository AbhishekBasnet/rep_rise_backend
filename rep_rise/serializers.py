from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .ml_logic import generate_workout_plan, attach_video_links, initialize_progress

from .models import StepLog, Profile,WorkoutRecommendation
from django.contrib.auth.models import User


#For User/Profiles

class ProfileSerializer(serializers.ModelSerializer):
    bmi = serializers.ReadOnlyField()

    # Validation constraints
    target_weight = serializers.FloatField(required=True, min_value=20.0, max_value=500.0)
    height = serializers.FloatField(required=True, min_value=50.0, max_value=300.0)
    weight = serializers.FloatField(required=True, min_value=20.0, max_value=500.0)
    age = serializers.IntegerField(required=True, min_value=10, max_value=120)

    # STRICT VALIDATION: Must be a valid choice from models.py.
    # Cannot be null, cannot be empty string "".
    fitness_level = serializers.ChoiceField(
        choices=Profile.LEVEL_CHOICES,
        required=True,
        allow_null=False,
        allow_blank=False
    )

    daily_step_goal = serializers.IntegerField(required=False, min_value=1000)

    class Meta:
        model = Profile
        fields = [
            'id',
            'height',
            'weight',
            'target_weight',
            'age',
            'gender',
            'daily_step_goal',
            'fitness_goal',
            'fitness_level',
            'bmi'
        ]
        read_only_fields = ['id', 'user', 'bmi']

    def update(self, instance, validated_data):
        """
        Custom update to trigger ML logic ONLY if physical stats change.
        """
        # 1. Identify fields that trigger a re-calculation
        trigger_fields = [
            'weight', 'height', 'age', 'target_weight',
            'gender', 'fitness_goal', 'fitness_level'
        ]

        should_recalculate = False

        # 2. Check if any trigger field is actually changing
        for field in trigger_fields:
            if field in validated_data and validated_data[field] != getattr(instance, field):
                should_recalculate = True
                break

        # 3. Perform the standard database update
        # This saves the user's explicit choice (e.g., 'beginner') to the DB
        instance = super().update(instance, validated_data)

        # 4. Run ML Logic if needed
        if should_recalculate:
            # Calculate new plan using the USER'S selected fitness level
            result = generate_workout_plan(
                age=instance.age,
                height=instance.height,
                weight=instance.weight,
                ideal_weight=instance.target_weight,
                fitness_level=instance.fitness_level
            )

            if result['status'] == 'success':
                # Run the Pipeline
                raw_schedule = result['schedule']
                enriched_schedule = attach_video_links(raw_schedule)
                final_data = initialize_progress(enriched_schedule)

                # Save/Update the Recommendation
                WorkoutRecommendation.objects.update_or_create(
                    profile=instance,
                    defaults={
                        'data': final_data,
                        'saved_weight': instance.weight,
                        'saved_goal': result['meta']['goal'],
                        'saved_level': instance.fitness_level  # Save the level the user chose
                    }
                )

                # Update the Profile Goal
                # We update fitness_goal because weight changes might shift a user from
                # "maintenance" to "fat_loss" automatically, but we keep their chosen Level.
                instance.fitness_goal = result['meta']['goal']

                # We do NOT update fitness_level here anymore, because the user explicitly set it.
                instance.save(update_fields=['fitness_goal'])

        return instance

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

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)




class StepLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = StepLog
        fields = ['date', 'step_count', 'calories_burned', 'distance_meters', 'duration_minutes']
        extra_kwargs = {
            'calories_burned': {'read_only': True},
            'distance_meters': {'read_only': True},
            'duration_minutes': {'read_only': True}
        }

    def create(self, validated_data):
        user = self.context['request'].user
        date = validated_data['date']
        new_steps = validated_data['step_count']

        # 1. OPTIMIZATION: Check if steps are same as DB to avoid re-calc
        # We fetch the most recent log for this day
        existing_log = StepLog.objects.filter(user=user, date=date).first()

        if existing_log and existing_log.step_count == new_steps:
            # Data is identical, return existing without touching DB or CPU
            return existing_log

        # 2. CALCULATION LOGIC (Only runs if steps changed)
        # Defaults
        calories = 0.0
        distance = 0.0
        duration = 0

        if new_steps > 0:
            # Get user stats (Handle defaults if profile is incomplete)
            try:
                profile = user.profile
                height_cm = profile.height if profile.height else 170.0  # fallback
                weight_kg = profile.weight if profile.weight else 70.0  # fallback
            except:
                height_cm = 170.0
                weight_kg = 70.0

            # A. Stride Length (approx 0.414 * height)
            stride_m = (height_cm * 0.414) / 100

            # B. Distance (Meters)
            distance = new_steps * stride_m

            # C. Calories (Simple formula: Distance(km) * Weight * 1.036)
            dist_km = distance / 1000
            calories = dist_km * weight_kg * 1.036

            # D. Duration (Minutes) - Assuming avg cadence of 100 steps/min
            duration = int(new_steps / 100)

        # 3. SAVE TO DB
        step_log, created = StepLog.objects.update_or_create(
            user=user,
            date=date,
            defaults={
                'step_count': new_steps,
                'calories_burned': round(calories, 2),
                'distance_meters': round(distance, 2),
                'duration_minutes': duration
            }
        )
        return step_log




class WorkoutRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutRecommendation
        fields = ['data', 'updated_at']
        # 'data' contains the JSON generated by ml_logic

class WorkoutProgressSerializer(serializers.Serializer):
    day_name = serializers.CharField(required=True)
    is_done = serializers.BooleanField(required=True)
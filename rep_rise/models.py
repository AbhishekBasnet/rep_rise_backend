from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]

    GOAL_CHOICES = [
        ('muscle_gain', 'Muscle Gain'),
        ('fat_loss', 'Fat Loss'),
        ('maintenance', 'Maintenance'),
    ]

    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('expert', 'Expert'),
    ]

    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)

    # Physical Attributes
    height = models.FloatField(help_text="Height in cm", null=True, blank=True)
    weight = models.FloatField(help_text="Current Weight in kg", null=True, blank=True)

    # Required for ML Logic (ideal_weight)
    target_weight = models.FloatField(help_text="Target/Ideal Weight in kg", null=True, blank=True)

    age = models.PositiveIntegerField(help_text="Age in years", null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)

    # Preferences
    fitness_goal = models.CharField(max_length=20, choices=GOAL_CHOICES, null=True, blank=True)

    # Changed to NULL so ML logic can auto-calculate it if user doesn't specify
    fitness_level = models.CharField(max_length=20, choices=LEVEL_CHOICES, null=True, blank=True)

    daily_step_goal = models.PositiveIntegerField(default=10000, help_text="Default baseline goal")

    # Auth / Security
    is_email_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    def is_otp_valid(self, otp):
        if self.otp_code == otp and self.otp_created_at:
            expiration = self.otp_created_at + timezone.timedelta(minutes=2)
            return timezone.now() < expiration
        return False

    @property
    def bmi(self):
        if self.height and self.weight:
            height_m = self.height / 100
            return round(self.weight / (height_m ** 2), 2)
        return None

    def __str__(self):
        return f"{self.user.username}'s Profile"


class StepLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='step_logs')
    date = models.DateField()
    step_count = models.PositiveIntegerField(default=0)
    calories_burned = models.FloatField(default=0, help_text="Energy expenditure in kcal")
    distance_meters = models.FloatField(default=0, help_text="Distance travelled in meters")
    duration_minutes = models.PositiveIntegerField(default=0, help_text="Time spent active in minutes")


    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']


class WorkoutRecommendation(models.Model):
    profile = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        related_name='recommendation'
    )


    data = models.JSONField(default=dict, help_text="The generated workout plan")
    saved_weight = models.FloatField(null=True, blank=True)
    saved_goal = models.CharField(max_length=20, null=True, blank=True)
    saved_level = models.CharField(max_length=20, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_outdated(self):
        """
        Returns True if the User's current Profile differs from
        the data we used to generate the last recommendation.
        """
        return (
                self.profile.weight != self.saved_weight or
                self.profile.fitness_goal != self.saved_goal or
                self.profile.fitness_level != self.saved_level
        )

    def __str__(self):
        return f"Recommendation for {self.profile.user.username}"


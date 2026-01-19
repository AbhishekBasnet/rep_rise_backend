from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Profile(models.Model):
    GENDER_CHOICES = [
        ('male', 'male'),
        ('female', 'female'),
    ]

    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    daily_step_goal = models.PositiveIntegerField(default=10000, help_text="Default baseline goal")
    height = models.FloatField(help_text="Height in cm", null=True, blank=True)
    weight = models.FloatField(help_text="Weight in kg", null=True, blank=True)
    # Changed birth_date to age as requested
    age = models.PositiveIntegerField(help_text="Age in years", null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        null=True,
        blank=True
    )


    @property
    def bmi(self):
        if self.height and self.weight:
            return self.weight / ((self.height / 100) ** 2)
        return None


    def __str__(self):
        return f"{self.user.username}'s Profile"

class StepGoalPlan(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goal_plans')
    start_date = models.DateField()
    end_date = models.DateField()
    target_steps = models.PositiveIntegerField()
    description = models.CharField(max_length=100, blank=True, help_text="")

    class Meta:
        ordering = ['-start_date']

    def clean(self):
        if self.start_date > self.end_date:
            raise ValidationError("Start date cannot be after end date.")

    def __str__(self):
        return f"{self.user.username}: {self.target_steps} steps ({self.start_date} to {self.end_date})"



class StepLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='step_logs')
    date = models.DateField()
    step_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'date')  # Ensures one entry per day per user
        ordering = ['-date']

class StepGoalOverride(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='step_overrides')
    date = models.DateField()
    target_steps = models.PositiveIntegerField()

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['date']

    def __str__(self):
        return f"{self.user.username} - {self.date}: {self.target_steps}"





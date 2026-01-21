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


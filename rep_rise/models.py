from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class Profile(models.Model):
    GOAL_CHOICES = [
        ('weight_loss', 'Weight Loss'),
        ('muscle_gain', 'Muscle Gain'),
        ('maintenance', 'Maintenance'),
    ]

    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    height = models.FloatField(help_text="Height in cm", null=True, blank=True)
    weight = models.FloatField(help_text="Weight in kg", null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    activity_level = models.FloatField(default=1.2, help_text="1.2 (sedentary) to 1.9 (active)")
    fitness_goal = models.CharField(max_length=20, choices=GOAL_CHOICES, default='maintenance')

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

    class Meta:
        unique_together = ('user', 'date')  # Ensures one entry per day per user
        ordering = ['-date']


class MuscleGroup(models.Model):
    name = models.CharField(max_length=50, unique=True)  # e.g., 'Chest', 'Quads'
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Workout(models.Model):
    DIFFICULTY_LEVELS = [('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced')]

    title = models.CharField(max_length=255)
    video_url = models.URLField()
    muscle_groups = models.ManyToManyField(MuscleGroup, related_name='workouts')
    calories_burned_per_minute = models.FloatField()
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_LEVELS)

    def __str__(self):
        return self.title


class FoodItem(models.Model):
    name = models.CharField(max_length=255)
    calories_per_100g = models.FloatField()
    protein = models.FloatField()
    carbs = models.FloatField()
    fats = models.FloatField()

    # Links food to specific workouts (for your future AI/Recommendation engine)
    recommended_for = models.ManyToManyField(Workout, related_name='recommended_foods', blank=True)

    def __str__(self):
        return self.name
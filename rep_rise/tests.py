import pandas as pd
from unittest.mock import patch
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status

from rep_rise.models import Profile, StepLog, WorkoutRecommendation
from rep_rise.ml_logic import calculate_bmi, get_workout_goal, get_fitness_level


class RepRiseAPITests(APITestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username='diznuts_test',
            password='strongpassword123',
            email='test@example.com'
        )

        Profile.objects.create(user=self.user)

        self.login_url = reverse('token-obtain-pair')
        self.register_url = reverse('auth-register')
        self.check_username_url = reverse('check-username')

        self.profile_url = reverse('profile-manage')
        self.steps_url = reverse('step-log-update')
        self.recommendation_url = reverse('workout-recommendation')
        self.progress_url = reverse('workout-progress-update')


        response = self.client.post(self.login_url, {
            'username': 'diznuts_test',
            'password': 'strongpassword123'
        })
        self.token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')



    def test_user_registration(self):
        """TC-01: Register a new user."""
        data = {
            'username': 'new_user',
            'password': 'newpassword123',
            'email': 'new@example.com'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertTrue(User.objects.filter(username='new_user').exists())
        self.assertTrue(Profile.objects.filter(user__username='new_user').exists())

    def test_check_username_taken(self):
        """TC-02: Check if existing username is taken."""
        response = self.client.get(self.check_username_url, {'username': 'diznuts_test'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_taken'])
        self.assertFalse(response.data['available'])


    def test_calculate_bmi(self):
        """TC-08: Test BMI Calculation."""
        # 70kg, 175cm -> 70 / (1.75^2) = 22.86
        bmi = calculate_bmi(70, 175)
        self.assertEqual(bmi, 22.86)

    def test_get_workout_goal(self):
        """TC-09: Test workout goal logic."""
        self.assertEqual(get_workout_goal(90, 75), "fat_loss")
        self.assertEqual(get_workout_goal(60, 75), "muscle_gain")
        self.assertEqual(get_workout_goal(75, 75), "maintenance")

    def test_get_fitness_level(self):
        """TC-10: Test fitness level constraints."""
        self.assertEqual(get_fitness_level(age=50, bmi=22), "beginner")  # Rule 1: Age > 45
        self.assertEqual(get_fitness_level(age=30, bmi=31), "beginner")  # Rule 1: BMI >= 30
        self.assertEqual(get_fitness_level(age=30, bmi=22), "intermediate")  # Rule 3

    # --- CATEGORY: USER PROFILE & PIPELINE TRIGGER ---

    @patch('rep_rise.ml_logic.load_data')
    def test_profile_update_triggers_ml(self, mock_load_data):
        """TC-03: Updating profile physical stats should trigger ML plan generation."""
        dummy_df = pd.DataFrame({
            'Workout': ['Bench Press', 'Squat', 'Bicep Curl'],
            'Body Part': ['chest', 'legs', 'arms'],
            'Type of Muscle': ['chest', 'quads', 'biceps']
        })
        mock_load_data.return_value = dummy_df

        data = {
            'height': 180,
            'weight': 80,
            'target_weight': 75,
            'age': 25,
            'gender': 'male'  # Ensure your model accepts lowercase 'male'
        }


        response = self.client.patch(self.profile_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.profile.refresh_from_db()
        self.assertTrue(hasattr(self.user.profile, 'recommendation'))
        self.assertIsNotNone(self.user.profile.recommendation.data)

        self.assertEqual(self.user.profile.fitness_goal, 'fat_loss')

    # --- CATEGORY: STEP TRACKING ---

    def test_step_log_calculation(self):
        """TC-04: Test step log creates accurate distance and calories."""

        profile = self.user.profile
        profile.height = 170.0
        profile.weight = 70.0
        profile.save()

        data = {
            'date': '2026-02-13',
            'step_count': 5000
        }
        response = self.client.post(self.steps_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Based on serializer logic:
        # stride_m = (170 * 0.414) / 100 = 0.7038m
        # distance = 5000 * 0.7038 = 3519.0m
        # calories = (3519.0 / 1000) * 70.0 * 1.036 = 255.19 kcal
        # duration = 5000 / 100 = 50 mins

        self.assertAlmostEqual(response.data['distance_meters'], 3519.0, places=1)
        self.assertAlmostEqual(response.data['calories_burned'], 255.19, places=1)
        self.assertEqual(response.data['duration_minutes'], 50)

    # --- CATEGORY: AI WORKOUT PROGRESS ---

    def test_workout_progress_update(self):
        """TC-07: Test patching workout progress."""
        mock_data = {
            "schedule": {"Day 1": []},
            "progress": {"Day 1": False}
        }
        WorkoutRecommendation.objects.create(
            profile=self.user.profile,
            data=mock_data
        )

        data = {
            'day_name': 'Day 1',
            'is_done': True
        }
        response = self.client.patch(self.progress_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        rec = WorkoutRecommendation.objects.get(profile=self.user.profile)
        self.assertTrue(rec.data['progress']['Day 1'])

    def test_incomplete_profile_recommendation_block(self):
        """TC-06: API should block recommendations if profile is missing stats."""

        response = self.client.get(self.recommendation_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Profile incomplete", response.data['error'])
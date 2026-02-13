
from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from rep_rise.views import StepLogUpdateView, StepLogAnalyticsView, RegisterView, CustomTokenObtainPairView, LogoutView, \
    ProfileManageView, UsernameCheckView, CurrentUserView, WorkoutRecommendationView, WorkoutProgressView

urlpatterns = [
    path('admin/', admin.site.urls),


    ################## AUTH #######################
    path('api/v1/auth/register/', RegisterView.as_view(), name='auth-register'),
    path('api/v1/auth/check-username/', UsernameCheckView.as_view(), name='check-username'),
    path('api/v1/auth/login/', CustomTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('api/v1/auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),


    ################## STEPS #######################
    path('api/v1/steps/', StepLogUpdateView.as_view(), name='step-log-update'),
    path('api/v1/steps/analytics/', StepLogAnalyticsView.as_view(), name='step-log-analytics'),



    ################## PROFILE #######################
    path('api/v1/user/profile/', ProfileManageView.as_view(), name='profile-manage'),
    path('api/v1/user/me/', CurrentUserView.as_view(), name='current-user-detail'),

    ################## RECOMMENDATION MODEL #######################
    path('api/v1/ai/recommendation/', WorkoutRecommendationView.as_view(), name='workout-recommendation'),
    path('api/v1/ai/recommendation/complete/', WorkoutProgressView.as_view(), name='workout-progress-update'),
    ################## .... #######################


]

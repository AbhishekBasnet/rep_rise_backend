
from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from rep_rise.views import StepLogUpdateView, StepLogAnalyticsView, RegisterView, CustomTokenObtainPairView, LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/steps/', StepLogUpdateView.as_view(), name='step-log-update'),
    path('api/v1/steps/analytics/', StepLogAnalyticsView.as_view(), name='step-log-analytics'),
    path('api/v1/auth/register/', RegisterView.as_view(), name='auth-register'),
    path('api/v1/auth/login/', CustomTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('api/v1/auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
]

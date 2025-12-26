
from django.contrib import admin
from django.urls import path

from rep_rise.views import StepLogUpdateView, StepLogAnalyticsView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/steps/', StepLogUpdateView.as_view(), name='step-log-update'),
    path('api/v1/steps/analytics/', StepLogAnalyticsView.as_view(), name='step-log-analytics'),
]

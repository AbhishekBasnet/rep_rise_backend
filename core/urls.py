
from django.contrib import admin
from django.urls import path

from rep_rise.views import StepLogUpdateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/steps/', StepLogUpdateView.as_view(), name='step-log-update'),
]

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import json

from .models import Profile, StepLog, WorkoutRecommendation


# --- Inline Classes ---

class StepLogInline(admin.TabularInline):
    """Allows viewing recent step logs directly inside the User/Profile view"""
    model = StepLog
    extra = 0
    readonly_fields = ('date', 'step_count', 'calories_burned')
    can_delete = False
    max_num = 7
    ordering = ('-date',)


class WorkoutRecommendationInline(admin.StackedInline):
    """Shows the current active recommendation inside the Profile"""
    model = WorkoutRecommendation
    extra = 0
    can_delete = False
    readonly_fields = ('updated_at', 'is_outdated_display')
    exclude = ('data',)

    def is_outdated_display(self, obj):
        return obj.is_outdated()

    is_outdated_display.boolean = True
    is_outdated_display.short_description = "Is Outdated?"


# --- Main Admin Classes ---

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'gender',
        'age',
        'current_stats',
        'fitness_goal',
        'fitness_level',
        'is_email_verified'
    )
    list_filter = ('fitness_goal', 'fitness_level', 'gender', 'is_email_verified')
    search_fields = ('user__username', 'user__email', 'user__first_name')
    list_per_page = 25

    fieldsets = (
        ('User Identity', {
            'fields': ('user', 'is_email_verified', 'otp_code', 'otp_created_at')
        }),
        ('Physical Attributes', {
            'fields': (('height', 'weight', 'bmi_display'), ('age', 'gender'))
        }),
        ('Fitness Logic', {
            'fields': (('fitness_goal', 'target_weight'), 'fitness_level', 'daily_step_goal'),
            'description': "These fields directly influence the ML generation logic."
        }),
    )

    readonly_fields = ('bmi_display',)

    def current_stats(self, obj):
        if obj.weight and obj.height:
            return f"{obj.weight}kg / {obj.height}cm"
        return "N/A"

    current_stats.short_description = "Weight/Height"

    def bmi_display(self, obj):
        return obj.bmi

    bmi_display.short_description = "BMI"


@admin.register(StepLog)
class StepLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'step_count', 'distance_km', 'calories_burned')
    list_filter = ('date',)
    search_fields = ('user__username',)
    date_hierarchy = 'date'
    ordering = ('-date',)

    def distance_km(self, obj):
        return f"{obj.distance_meters / 1000:.2f} km"

    distance_km.short_description = "Distance (km)"


@admin.register(WorkoutRecommendation)
class WorkoutRecommendationAdmin(admin.ModelAdmin):
    list_display = ('profile', 'updated_at', 'status_badge')
    search_fields = ('profile__user__username',)
    readonly_fields = ('updated_at', 'json_visualizer')
    exclude = ('data',)

    fieldsets = (
        ('Meta Data', {
            'fields': ('profile', 'updated_at', 'saved_weight', 'saved_goal', 'saved_level')
        }),
        ('Generated Plan', {
            'fields': ('json_visualizer',),
            'classes': ('collapse',),
        }),
    )

    def status_badge(self, obj):
        # FIX: Used mark_safe here because the HTML is static (no variables to format)
        if obj.is_outdated():
            return mark_safe(
                '<span style="background-color: #ffc107; color: black; padding: 3px 10px; border-radius: 10px; font-weight: bold;">Outdated</span>'
            )
        return mark_safe(
            '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 10px; font-weight: bold;">Active</span>'
        )

    status_badge.short_description = "Status"

    def json_visualizer(self, obj):
        """
        Pretty-prints the JSON data field.
        """
        try:
            data_str = json.dumps(obj.data, indent=4, sort_keys=True)
            style = "background-color: #2b2b2b; color: #f8f8f2; padding: 10px; border-radius: 5px; white-space: pre-wrap; font-family: monospace;"

            # This usage is correct because we are passing variables into the string
            return format_html('<pre style="{}">{}</pre>', style, data_str)
        except Exception as e:
            return f"Error parsing JSON: {e}"

    json_visualizer.short_description = "Workout Plan Data"
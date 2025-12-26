from rest_framework import serializers
from .models import StepLog

class StepLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = StepLog
        fields = ['date', 'step_count']

    def create(self, validated_data):
        # Extract user from the request context provided by the view
        user = self.context['request'].user
        date = validated_data.get('date')
        step_count = validated_data.get('step_count')

        # Use update_or_create to handle the unique_together constraint 
        step_log, created = StepLog.objects.update_or_create(
            user=user,
            date=date,
            defaults={'step_count': step_count}
        )
        return step_log
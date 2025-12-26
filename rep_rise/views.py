from .serializers import StepLogSerializer
from django.db.models import Sum
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import StepLog

class StepLogUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = StepLogSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StepLogAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        period = request.query_params.get('period', 'daily')

        # Clean query without citation text
        queryset = StepLog.objects.filter(user=user)

        if period == 'weekly':
            data = (
                queryset.annotate(period_label=TruncWeek('date'))
                .values('period_label')
                .annotate(total_steps=Sum('step_count'))
                .order_by('-period_label')
            )
        elif period == 'monthly':
            data = (
                queryset.annotate(period_label=TruncMonth('date'))
                .values('period_label')
                .annotate(total_steps=Sum('step_count'))
                .order_by('-period_label')
            )
        else:
            # Daily (individual entries)
            data = queryset.values('date', 'step_count').order_by('-date')

        return Response({
            "period": period,
            "results": list(data)
        }, status=status.HTTP_200_OK)
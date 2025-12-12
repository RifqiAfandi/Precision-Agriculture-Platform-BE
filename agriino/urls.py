from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DeviceViewSet, AreaViewSet, AnalysisResultViewSet,
    KrigingAnalysisView, SyncDeviceDataView,
    quick_analysis, health_check
)

router = DefaultRouter()
router.register(r'devices', DeviceViewSet, basename='device')
router.register(r'areas', AreaViewSet, basename='area')
router.register(r'analysis-results', AnalysisResultViewSet, basename='analysis-result')

urlpatterns = [
    # Router URLs (CRUD for devices, areas, analysis results)
    path('', include(router.urls)),
    
    # Kriging analysis endpoints
    path('analyze/', KrigingAnalysisView.as_view(), name='kriging-analyze'),
    path('quick-analyze/', quick_analysis, name='quick-analyze'),
    
    # Data sync endpoint
    path('sync/', SyncDeviceDataView.as_view(), name='sync-device-data'),
    
    # Health check
    path('health/', health_check, name='health-check'),
]

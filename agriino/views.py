from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db import transaction
import logging

from .models import Device, DeviceData, Area, AreaDevice, AnalysisResult, KrigingGrid
from .serializers import (
    DeviceSerializer, DeviceCreateSerializer, DeviceDataSerializer,
    AreaSerializer, AreaCreateSerializer, AreaDeviceSerializer,
    AnalysisResultSerializer, AnalysisResultSummarySerializer,
    KrigingAnalysisRequestSerializer, KrigingAnalysisResponseSerializer,
    BulkDeviceDataSerializer
)
from .services.kriging_service import analyze_nitrogen_levels, KrigingService

logger = logging.getLogger(__name__)


class DeviceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing devices.
    
    Provides CRUD operations for agricultural sensor devices.
    """
    queryset = Device.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return DeviceCreateSerializer
        return DeviceSerializer
    
    @action(detail=True, methods=['get'])
    def data(self, request, pk=None):
        """Get all data points for a specific device."""
        device = self.get_object()
        data_points = device.data_points.all()[:100]  # Limit to last 100
        serializer = DeviceDataSerializer(data_points, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_data(self, request, pk=None):
        """Add new data point to a device."""
        device = self.get_object()
        serializer = DeviceDataSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(device=device)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AreaViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing agricultural areas.
    
    Provides CRUD operations for farm areas marked on the map.
    """
    queryset = Area.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AreaCreateSerializer
        return AreaSerializer
    
    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'])
    def add_device(self, request, pk=None):
        """Add a device to this area."""
        area = self.get_object()
        device_id = request.data.get('device_id')
        
        try:
            device = Device.objects.get(id=device_id)
            area_device, created = AreaDevice.objects.get_or_create(area=area, device=device)
            
            if created:
                return Response(
                    {'message': f'Device {device.device_id} added to area {area.name}'},
                    status=status.HTTP_201_CREATED
                )
            return Response(
                {'message': 'Device already in this area'},
                status=status.HTTP_200_OK
            )
        except Device.DoesNotExist:
            return Response(
                {'error': 'Device not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['delete'])
    def remove_device(self, request, pk=None):
        """Remove a device from this area."""
        area = self.get_object()
        device_id = request.data.get('device_id')
        
        try:
            area_device = AreaDevice.objects.get(area=area, device_id=device_id)
            area_device.delete()
            return Response(
                {'message': 'Device removed from area'},
                status=status.HTTP_200_OK
            )
        except AreaDevice.DoesNotExist:
            return Response(
                {'error': 'Device not in this area'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def devices(self, request, pk=None):
        """Get all devices in this area."""
        area = self.get_object()
        area_devices = area.area_devices.all()
        serializer = AreaDeviceSerializer(area_devices, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def analysis_history(self, request, pk=None):
        """Get analysis history for this area."""
        area = self.get_object()
        analyses = area.analysis_results.all()[:20]
        serializer = AnalysisResultSummarySerializer(analyses, many=True)
        return Response(serializer.data)


class AnalysisResultViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing analysis results.
    
    Provides read-only access to Kriging analysis results.
    """
    queryset = AnalysisResult.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AnalysisResultSerializer
        return AnalysisResultSummarySerializer


class KrigingAnalysisView(APIView):
    """
    API endpoint for performing Kriging analysis on nitrogen data.
    
    This is the main endpoint that receives data from the frontend (which gets it from Firebase)
    and performs spatial interpolation using Ordinary Kriging.
    
    Flow: Firebase -> Frontend -> This API -> Frontend (with analysis results)
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """
        Perform Kriging analysis on the provided device data.
        
        Request body should contain:
        - device_data: List of device readings with lat, lng, nitrogen values
        - Optional: grid_resolution, variogram_model, thresholds, bounds
        
        Returns:
        - grid_points: Interpolated values with classifications (high/normal/low)
        - input_points: Original device data with classifications
        - statistics: Summary statistics of the analysis
        """
        serializer = KrigingAnalysisRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid request data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            # Prepare device data for Kriging
            device_data = [
                {
                    'latitude': d['lat'],
                    'longitude': d['lng'],
                    'nitrogen': d['nitrogen'],
                    'device_id': d['device_id']
                }
                for d in data['device_data']
            ]
            
            # Prepare bounds if provided
            grid_bounds = None
            if all([data.get('min_lat'), data.get('max_lat'), 
                    data.get('min_lng'), data.get('max_lng')]):
                grid_bounds = {
                    'min_lat': data['min_lat'],
                    'max_lat': data['max_lat'],
                    'min_lng': data['min_lng'],
                    'max_lng': data['max_lng'],
                }
            
            # Perform Kriging analysis with new parameters
            result = analyze_nitrogen_levels(
                device_data=device_data,
                grid_bounds=grid_bounds,
                grid_resolution=data['grid_resolution'],
                variogram_model=data['variogram_model'],
                low_threshold=data['low_threshold'],
                high_threshold=data['high_threshold'],
                influence_radius=data.get('influence_radius', 0.05),  # Default 50m
                deficient_threshold=data.get('deficient_threshold', 1.80),
                subnormal_threshold=data.get('subnormal_threshold', 2.71),
                normal_threshold=data.get('normal_threshold', 3.31)
            )
            
            # Optionally save to database
            analysis_id = None
            if data.get('area_id'):
                try:
                    area = Area.objects.get(id=data['area_id'])
                    analysis_id = self._save_analysis_result(area, data, result)
                except Area.DoesNotExist:
                    logger.warning(f"Area with id {data['area_id']} not found, skipping save")
            
            response_data = {
                'success': True,
                'message': 'Kriging analysis completed successfully',
                'analysis_id': analysis_id,
                'grid_points': result['grid_points'],
                'input_points': result['input_points'],
                'statistics': result['statistics'],
                'bounds': result['bounds'],
                'thresholds': result['thresholds'],
                'variogram_params': result['variogram_params'],
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ValueError as e:
            logger.error(f"Kriging analysis error: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.exception("Unexpected error during Kriging analysis")
            return Response({
                'success': False,
                'message': 'An unexpected error occurred during analysis'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @transaction.atomic
    def _save_analysis_result(self, area, data, result):
        """Save the analysis result to the database."""
        stats = result['statistics']
        variogram = result['variogram_params']
        
        analysis = AnalysisResult.objects.create(
            area=area,
            analysis_type='nitrogen',
            status='completed',
            variogram_model=variogram['model'],
            nugget=variogram['nugget'],
            sill=variogram['sill'],
            range_param=variogram['range'],
            low_threshold=data['low_threshold'],
            high_threshold=data['high_threshold'],
            min_value=stats['min_value'],
            max_value=stats['max_value'],
            mean_value=stats['mean_value'],
            std_value=stats['std_value'],
            completed_at=timezone.now()
        )
        
        # Save grid points
        grid_objects = [
            KrigingGrid(
                analysis_result=analysis,
                latitude=point['latitude'],
                longitude=point['longitude'],
                predicted_value=point['predicted_value'],
                variance=point['variance'],
                classification=point['classification']
            )
            for point in result['grid_points']
        ]
        KrigingGrid.objects.bulk_create(grid_objects)
        
        return analysis.id


class SyncDeviceDataView(APIView):
    """
    API endpoint for syncing device data from Firebase.
    
    This endpoint can be used to:
    1. Store device data in the database for historical tracking
    2. Update device locations and sensor readings
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """
        Sync device data from Firebase to the database.
        
        Request body should contain:
        - devices: List of device data from Firebase
        - save_to_db: Whether to save the data to database (default: False)
        """
        serializer = BulkDeviceDataSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid request data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        if not data.get('save_to_db', False):
            return Response({
                'success': True,
                'message': 'Data validated but not saved (save_to_db is False)',
                'device_count': len(data['devices'])
            })
        
        try:
            created_count = 0
            updated_count = 0
            data_count = 0
            
            with transaction.atomic():
                for device_data in data['devices']:
                    # Get or create device
                    device, created = Device.objects.update_or_create(
                        device_id=device_data['device_id'],
                        defaults={
                            'latitude': device_data['lat'],
                            'longitude': device_data['lng'],
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                    
                    # Create device data record
                    DeviceData.objects.create(
                        device=device,
                        nitrogen=device_data['nitrogen'],
                        spad=device_data.get('spad'),
                        a_rgb=device_data.get('A_RGB'),
                        a_r=device_data.get('A_R'),
                        a_g=device_data.get('A_G'),
                        a_b=device_data.get('A_B'),
                        r=device_data.get('R'),
                        g=device_data.get('G'),
                        b=device_data.get('B'),
                        o=device_data.get('O'),
                        v=device_data.get('V'),
                        y=device_data.get('Y'),
                        t_r=device_data.get('T_R'),
                        t_g=device_data.get('T_G'),
                        t_b=device_data.get('T_B'),
                        eq1=device_data.get('eq1'),
                        eq2=device_data.get('eq2'),
                        class_eq1=device_data.get('class_eq1'),
                        class_eq2=device_data.get('class_eq2'),
                        firebase_timestamp=device_data.get('timestamp'),
                    )
                    data_count += 1
            
            return Response({
                'success': True,
                'message': 'Device data synced successfully',
                'devices_created': created_count,
                'devices_updated': updated_count,
                'data_points_created': data_count
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.exception("Error syncing device data")
            return Response({
                'success': False,
                'message': f'Error syncing data: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def quick_analysis(request):
    """
    Quick Kriging analysis endpoint for simple requests.
    
    Accepts a simplified request format:
    {
        "points": [
            {"lat": -8.123, "lng": 113.456, "nitrogen": 2.1},
            {"lat": -8.124, "lng": 113.457, "nitrogen": 1.8},
            ...
        ],
        "resolution": 20,  // optional
        "model": "spherical",  // optional
    }
    
    Returns the analysis results directly.
    """
    points = request.data.get('points', [])
    
    if not points or len(points) < 1:
        return Response({
            'success': False,
            'message': 'At least 1 data point is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        device_data = [
            {
                'latitude': p.get('lat', p.get('latitude')),
                'longitude': p.get('lng', p.get('longitude')),
                'nitrogen': p['nitrogen']
            }
            for p in points
        ]
        
        result = analyze_nitrogen_levels(
            device_data=device_data,
            grid_resolution=request.data.get('resolution', 20),
            variogram_model=request.data.get('model', 'spherical'),
            low_threshold=request.data.get('low_threshold', 1.5),
            high_threshold=request.data.get('high_threshold', 2.5)
        )
        
        return Response({
            'success': True,
            **result
        })
        
    except Exception as e:
        logger.exception("Error in quick analysis")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """Health check endpoint for the Agriino API."""
    return Response({
        'status': 'healthy',
        'service': 'Agriino Kriging Analysis API',
        'version': '1.0.0'
    })

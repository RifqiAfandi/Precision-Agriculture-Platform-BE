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
    KrigingAnalysisRequestSerializer,
    BulkDeviceDataSerializer
)
from .services.kriging_service import analyze_nitrogen_levels
from agriino.constants import DEFAULT_INFLUENCE_RADIUS_KM

logger = logging.getLogger(__name__)


class DeviceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing devices.
    
    Provides CRUD operations for agricultural sensor devices.
    Supports ?no_page=true query parameter to disable pagination and return all devices.
    """
    queryset = Device.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def list(self, request, *args, **kwargs):
        """Auto-sync with Firebase Firestore on every list request to get real-time data."""
        try:
            from agriino.services.firebase_sync import sync_firebase_to_db
            sync_firebase_to_db()
        except Exception as e:
            logger.error(f"Auto-sync with Firebase failed: {e}")
        return super().list(request, *args, **kwargs)
    
    def paginate_queryset(self, queryset):
        """Disable pagination when ?no_page=true is passed."""
        if self.request.query_params.get('no_page', '').lower() == 'true':
            return None
        return super().paginate_queryset(queryset)
    
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

    @action(detail=False, methods=['get'])
    def daily_averages(self, request):
        """Get daily average measurements grouped by date."""
        from datetime import datetime
        import collections
        
        daily_groups = collections.defaultdict(list)
        for data in DeviceData.objects.select_related('device').all().order_by('firebase_timestamp', 'created_at'):
            ts = data.firebase_timestamp
            if ts:
                dt = datetime.fromtimestamp(ts / 1000.0)
            else:
                dt = data.created_at
                
            date_str = dt.strftime('%Y-%m-%d')
            daily_groups[date_str].append((dt, data))
            
        days_map = {
            'Monday': 'Sen', 'Tuesday': 'Sel', 'Wednesday': 'Rab', 'Thursday': 'Kam',
            'Friday': 'Jum', 'Saturday': 'Sab', 'Sunday': 'Min'
        }
        months_map = {
            1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'Mei', 6: 'Jun',
            7: 'Jul', 8: 'Agt', 9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Des'
        }
        
        daily_averages_list = []
        for date_str, items in sorted(daily_groups.items(), reverse=True):
            try:
                entry_date = datetime.strptime(date_str, '%Y-%m-%d')
                day_name = days_map.get(entry_date.strftime('%A'), entry_date.strftime('%a'))
                month_name = months_map.get(entry_date.month, entry_date.strftime('%b'))
                date_label = f"{day_name}, {entry_date.day} {month_name}"
            except Exception:
                date_label = date_str
                
            devices_data_for_day = []
            for dt, item in items:
                devices_data_for_day.append({
                    'device_id': item.device.device_id,
                    'name': item.device.name or f"Scan {item.device.device_id[:6]}",
                    'lat': item.device.latitude,
                    'lng': item.device.longitude,
                    'nitrogen': item.nitrogen,
                    'spad': item.spad,
                    'R': item.r,
                    'G': item.g,
                    'B': item.b,
                    'O': item.o,
                    'V': item.v,
                    'Y': item.y,
                    'timestamp': item.firebase_timestamp or int(dt.timestamp() * 1000),
                    'classification': item.class_eq1 or 'unknown'
                })
                
            nitrogens = [item[1].nitrogen for item in items if item[1].nitrogen is not None]
            spads = [item[1].spad for item in items if item[1].spad is not None]
            rs = [item[1].r for item in items if item[1].r is not None]
            gs = [item[1].g for item in items if item[1].g is not None]
            bs = [item[1].b for item in items if item[1].b is not None]
            
            avg_nitrogen = sum(nitrogens) / len(nitrogens) if nitrogens else 0
            avg_spad = sum(spads) / len(spads) if spads else 0
            avg_r = sum(rs) / len(rs) if rs else 0
            avg_g = sum(gs) / len(gs) if gs else 0
            avg_b = sum(bs) / len(bs) if bs else 0
            
            # classify average nitrogen
            if avg_nitrogen < 1.80:
                classification = 'deficient'
            elif avg_nitrogen < 2.71:
                classification = 'subnormal'
            elif avg_nitrogen < 3.31:
                classification = 'normal'
            else:
                classification = 'high'
                
            daily_averages_list.append({
                'date': date_str,
                'dateLabel': date_label,
                'avgNitrogen': avg_nitrogen,
                'avgSpad': avg_spad,
                'avgR': avg_r,
                'avgG': avg_g,
                'avgB': avg_b,
                'classification': classification,
                'devices': devices_data_for_day,
                'readingsCount': len(items)
            })
            
        return Response(daily_averages_list)



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
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
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
                influence_radius=data.get('influence_radius', DEFAULT_INFLUENCE_RADIUS_KM),
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
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def post(self, request):
        """
        Sync device data from Firebase to the database.
        
        If request body is empty or does not contain 'devices', this will connect 
        to Firebase Firestore using the backend service credentials and sync all scans.
        Otherwise, syncs the provided devices list.
        """
        if not request.data or 'devices' not in request.data:
            try:
                from .services.firebase_sync import sync_firebase_to_db
                stats = sync_firebase_to_db()
                return Response({
                    'success': True,
                    'message': 'Device data synced from Firestore successfully',
                    'devices_created': stats['devices_created'],
                    'devices_updated': stats['devices_updated'],
                    'data_points_created': stats['data_points_created']
                }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.exception("Error syncing from Firestore")
                return Response({
                    'success': False,
                    'message': f'Failed to sync from Firestore: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
                'message': 'An unexpected error occurred while syncing data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
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

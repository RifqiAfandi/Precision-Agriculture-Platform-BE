from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
import json

from .models import Device, DeviceData, Area, AreaDevice, AnalysisResult
from .services.kriging_service import KrigingService, analyze_nitrogen_levels


class KrigingServiceTests(TestCase):
    """Tests for the Kriging interpolation service."""
    
    def setUp(self):
        self.sample_data = [
            {'latitude': -8.1650, 'longitude': 113.7170, 'nitrogen': 2.1},
            {'latitude': -8.1655, 'longitude': 113.7175, 'nitrogen': 1.8},
            {'latitude': -8.1660, 'longitude': 113.7180, 'nitrogen': 2.5},
            {'latitude': -8.1645, 'longitude': 113.7165, 'nitrogen': 1.5},
        ]
    
    def test_kriging_service_initialization(self):
        """Test that KrigingService initializes correctly."""
        service = KrigingService(variogram_model='spherical')
        self.assertEqual(service.variogram_model_name, 'spherical')
        self.assertFalse(service._fitted)
    
    def test_kriging_service_fit(self):
        """Test fitting the Kriging model."""
        service = KrigingService()
        service.fit(self.sample_data)
        self.assertTrue(service._fitted)
        self.assertIsNotNone(service.nugget)
        self.assertIsNotNone(service.sill)
        self.assertIsNotNone(service.range_param)
    
    def test_kriging_prediction(self):
        """Test Kriging prediction at a point."""
        service = KrigingService()
        service.fit(self.sample_data)
        
        # Predict at a known location
        results = service.predict([(-8.1652, 113.7172)])
        
        self.assertEqual(len(results), 1)
        self.assertIn(results[0].classification, ['low', 'normal', 'high'])
    
    def test_kriging_grid_generation(self):
        """Test grid generation."""
        service = KrigingService()
        service.fit(self.sample_data)
        
        bounds = {
            'min_lat': -8.1665,
            'max_lat': -8.1645,
            'min_lng': 113.7165,
            'max_lng': 113.7185,
        }
        
        results = service.generate_grid(bounds, resolution=5)
        self.assertEqual(len(results), 25)  # 5x5 grid
    
    def test_analyze_nitrogen_levels(self):
        """Test the main analysis function."""
        result = analyze_nitrogen_levels(
            device_data=self.sample_data,
            grid_resolution=10
        )
        
        self.assertIn('grid_points', result)
        self.assertIn('statistics', result)
        self.assertIn('input_points', result)
        self.assertEqual(len(result['input_points']), 4)
    
    def test_classification_thresholds(self):
        """Test that classification works correctly."""
        service = KrigingService(low_threshold=1.5, high_threshold=2.5)
        
        self.assertEqual(service._classify_value(1.0), 'low')
        self.assertEqual(service._classify_value(2.0), 'normal')
        self.assertEqual(service._classify_value(3.0), 'high')


class KrigingAPITests(APITestCase):
    """Tests for the Kriging analysis API endpoints."""
    
    def test_health_check(self):
        """Test health check endpoint."""
        url = reverse('health-check')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')
    
    def test_quick_analysis(self):
        """Test quick analysis endpoint."""
        url = reverse('quick-analyze')
        data = {
            'points': [
                {'lat': -8.1650, 'lng': 113.7170, 'nitrogen': 2.1},
                {'lat': -8.1655, 'lng': 113.7175, 'nitrogen': 1.8},
                {'lat': -8.1660, 'lng': 113.7180, 'nitrogen': 2.5},
            ],
            'resolution': 10
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('grid_points', response.data)
        self.assertIn('statistics', response.data)
    
    def test_full_kriging_analysis(self):
        """Test full Kriging analysis endpoint."""
        url = reverse('kriging-analyze')
        data = {
            'device_data': [
                {
                    'device_id': 'device_001',
                    'lat': -8.1650,
                    'lng': 113.7170,
                    'nitrogen': 2.1,
                    'spad': 24.5
                },
                {
                    'device_id': 'device_002',
                    'lat': -8.1655,
                    'lng': 113.7175,
                    'nitrogen': 1.8,
                    'spad': 22.1
                },
            ],
            'grid_resolution': 10,
            'variogram_model': 'spherical',
            'low_threshold': 1.5,
            'high_threshold': 2.5
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
    
    def test_analysis_with_insufficient_data(self):
        """Test analysis with no data points."""
        url = reverse('quick-analyze')
        data = {'points': []}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])


class DeviceModelTests(TestCase):
    """Tests for the Device model."""
    
    def test_device_creation(self):
        """Test creating a device."""
        device = Device.objects.create(
            device_id='test_device_001',
            name='Test Sensor',
            latitude=-8.1650,
            longitude=113.7170
        )
        
        self.assertEqual(device.device_id, 'test_device_001')
        self.assertTrue(device.is_active)
    
    def test_device_data_creation(self):
        """Test creating device data."""
        device = Device.objects.create(
            device_id='test_device_002',
            latitude=-8.1650,
            longitude=113.7170
        )
        
        data = DeviceData.objects.create(
            device=device,
            nitrogen=2.1,
            spad=24.5
        )
        
        self.assertEqual(data.nitrogen, 2.1)
        self.assertEqual(data.device, device)


class AreaModelTests(TestCase):
    """Tests for the Area model."""
    
    def test_area_creation(self):
        """Test creating an area."""
        area = Area.objects.create(
            name='Test Field',
            description='A test agricultural field',
            polygon_coordinates=[
                [-8.1645, 113.7165],
                [-8.1665, 113.7165],
                [-8.1665, 113.7185],
                [-8.1645, 113.7185],
            ]
        )
        
        self.assertEqual(area.name, 'Test Field')
        self.assertEqual(len(area.polygon_coordinates), 4)
    
    def test_area_device_relationship(self):
        """Test adding devices to an area."""
        area = Area.objects.create(name='Test Field')
        device = Device.objects.create(
            device_id='test_device_003',
            latitude=-8.1650,
            longitude=113.7170
        )
        
        area_device = AreaDevice.objects.create(area=area, device=device)
        
        self.assertEqual(area.area_devices.count(), 1)
        self.assertEqual(area.area_devices.first().device, device)

from rest_framework import serializers
from .models import Device, DeviceData, Area, AreaDevice, AnalysisResult, KrigingGrid


class DeviceDataSerializer(serializers.ModelSerializer):
    """Serializer for device sensor data."""
    
    class Meta:
        model = DeviceData
        fields = [
            'id', 'nitrogen', 'spad', 'a_rgb', 'a_r', 'a_g', 'a_b',
            'r', 'g', 'b', 'o', 'v', 'y', 't_r', 't_g', 't_b',
            'eq1', 'eq2', 'class_eq1', 'class_eq2', 'firebase_timestamp', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for device information."""
    latest_data = serializers.SerializerMethodField()
    
    class Meta:
        model = Device
        fields = ['id', 'device_id', 'name', 'latitude', 'longitude', 'is_active', 'created_at', 'latest_data']
        read_only_fields = ['id', 'created_at']
    
    def get_latest_data(self, obj):
        latest = obj.data_points.first()
        if latest:
            return DeviceDataSerializer(latest).data
        return None


class DeviceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating devices."""
    
    class Meta:
        model = Device
        fields = ['device_id', 'name', 'latitude', 'longitude', 'is_active']


class AreaDeviceSerializer(serializers.ModelSerializer):
    """Serializer for area-device relationship."""
    device = DeviceSerializer(read_only=True)
    device_id = serializers.PrimaryKeyRelatedField(
        queryset=Device.objects.all(),
        source='device',
        write_only=True
    )
    
    class Meta:
        model = AreaDevice
        fields = ['id', 'device', 'device_id', 'added_at']
        read_only_fields = ['id', 'added_at']


class KrigingGridSerializer(serializers.ModelSerializer):
    """Serializer for Kriging grid points."""
    
    class Meta:
        model = KrigingGrid
        fields = ['id', 'latitude', 'longitude', 'predicted_value', 'variance', 'classification']
        read_only_fields = ['id']


class AnalysisResultSerializer(serializers.ModelSerializer):
    """Serializer for analysis results."""
    grid_points = KrigingGridSerializer(many=True, read_only=True)
    
    class Meta:
        model = AnalysisResult
        fields = [
            'id', 'area', 'analysis_type', 'status', 'variogram_model',
            'nugget', 'sill', 'range_param', 'low_threshold', 'high_threshold',
            'min_value', 'max_value', 'mean_value', 'std_value',
            'error_message', 'created_at', 'completed_at', 'grid_points'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at']


class AnalysisResultSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for analysis results without grid points."""
    
    class Meta:
        model = AnalysisResult
        fields = [
            'id', 'area', 'analysis_type', 'status', 'variogram_model',
            'min_value', 'max_value', 'mean_value', 'std_value',
            'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at']


class AreaSerializer(serializers.ModelSerializer):
    """Serializer for area information."""
    area_devices = AreaDeviceSerializer(many=True, read_only=True)
    device_count = serializers.SerializerMethodField()
    latest_analysis = serializers.SerializerMethodField()
    
    class Meta:
        model = Area
        fields = [
            'id', 'name', 'description', 'polygon_coordinates',
            'center_latitude', 'center_longitude', 'created_by',
            'created_at', 'updated_at', 'area_devices', 'device_count', 'latest_analysis'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def get_device_count(self, obj):
        return obj.area_devices.count()
    
    def get_latest_analysis(self, obj):
        latest = obj.analysis_results.filter(status='completed').first()
        if latest:
            return AnalysisResultSummarySerializer(latest).data
        return None


class AreaCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating areas."""
    device_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=[]
    )
    
    class Meta:
        model = Area
        fields = ['name', 'description', 'polygon_coordinates', 'center_latitude', 'center_longitude', 'device_ids']
    
    def create(self, validated_data):
        device_ids = validated_data.pop('device_ids', [])
        area = Area.objects.create(**validated_data)
        
        # Add devices to area
        for device_id in device_ids:
            try:
                device = Device.objects.get(id=device_id)
                AreaDevice.objects.create(area=area, device=device)
            except Device.DoesNotExist:
                pass
        
        return area


# Serializers for Firebase data processing

class FirebaseDeviceDataSerializer(serializers.Serializer):
    """Serializer for processing data from Firebase."""
    
    # Device identification
    device_id = serializers.CharField(required=True)
    
    # Location
    lat = serializers.FloatField(required=True)
    lng = serializers.FloatField(required=True)
    
    # Main values
    nitrogen = serializers.FloatField(required=True)
    spad = serializers.FloatField(required=False, allow_null=True)
    
    # RGB values
    A_RGB = serializers.FloatField(required=False, allow_null=True)
    A_R = serializers.FloatField(required=False, allow_null=True)
    A_G = serializers.FloatField(required=False, allow_null=True)
    A_B = serializers.FloatField(required=False, allow_null=True)
    R = serializers.FloatField(required=False, allow_null=True)
    G = serializers.FloatField(required=False, allow_null=True)
    B = serializers.FloatField(required=False, allow_null=True)
    O = serializers.FloatField(required=False, allow_null=True)
    V = serializers.FloatField(required=False, allow_null=True)
    Y = serializers.FloatField(required=False, allow_null=True)
    
    # Transmittance
    T_R = serializers.FloatField(required=False, allow_null=True)
    T_G = serializers.FloatField(required=False, allow_null=True)
    T_B = serializers.FloatField(required=False, allow_null=True)
    
    # Equations
    eq1 = serializers.FloatField(required=False, allow_null=True)
    eq2 = serializers.FloatField(required=False, allow_null=True)
    class_eq1 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    class_eq2 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    
    # Timestamp
    timestamp = serializers.IntegerField(required=False, allow_null=True)


class KrigingAnalysisRequestSerializer(serializers.Serializer):
    """Serializer for Kriging analysis request from frontend."""
    
    # Area information
    area_id = serializers.IntegerField(required=False, allow_null=True)
    area_name = serializers.CharField(required=False, allow_blank=True)
    
    # Device data from Firebase (list of device readings)
    device_data = serializers.ListField(
        child=FirebaseDeviceDataSerializer(),
        min_length=1
    )
    
    # Optional analysis parameters
    grid_resolution = serializers.IntegerField(default=20, min_value=5, max_value=100)
    variogram_model = serializers.ChoiceField(
        choices=['spherical', 'exponential', 'gaussian', 'linear'],
        default='spherical'
    )
    low_threshold = serializers.FloatField(default=1.5)
    high_threshold = serializers.FloatField(default=2.5)
    
    # Optional custom bounds
    min_lat = serializers.FloatField(required=False, allow_null=True)
    max_lat = serializers.FloatField(required=False, allow_null=True)
    min_lng = serializers.FloatField(required=False, allow_null=True)
    max_lng = serializers.FloatField(required=False, allow_null=True)
    
    def validate_device_data(self, value):
        if len(value) < 1:
            raise serializers.ValidationError("At least 1 device data point is required for analysis")
        return value


class KrigingGridPointResponseSerializer(serializers.Serializer):
    """Serializer for individual grid point in response."""
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    predicted_value = serializers.FloatField()
    variance = serializers.FloatField()
    classification = serializers.ChoiceField(choices=['low', 'normal', 'high'])


class InputPointResponseSerializer(serializers.Serializer):
    """Serializer for input point classification in response."""
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    nitrogen = serializers.FloatField()
    predicted_value = serializers.FloatField()
    classification = serializers.ChoiceField(choices=['low', 'normal', 'high'])


class StatisticsResponseSerializer(serializers.Serializer):
    """Serializer for analysis statistics in response."""
    min_value = serializers.FloatField()
    max_value = serializers.FloatField()
    mean_value = serializers.FloatField()
    std_value = serializers.FloatField()
    low_count = serializers.IntegerField()
    normal_count = serializers.IntegerField()
    high_count = serializers.IntegerField()
    total_points = serializers.IntegerField()
    variogram_model = serializers.CharField()
    nugget = serializers.FloatField()
    sill = serializers.FloatField()
    range = serializers.FloatField()


class KrigingAnalysisResponseSerializer(serializers.Serializer):
    """Serializer for the complete Kriging analysis response."""
    success = serializers.BooleanField()
    message = serializers.CharField()
    analysis_id = serializers.IntegerField(required=False, allow_null=True)
    
    grid_points = KrigingGridPointResponseSerializer(many=True)
    input_points = InputPointResponseSerializer(many=True)
    statistics = StatisticsResponseSerializer()
    
    bounds = serializers.DictField()
    thresholds = serializers.DictField()
    variogram_params = serializers.DictField()


class BulkDeviceDataSerializer(serializers.Serializer):
    """Serializer for bulk device data sync from Firebase."""
    devices = serializers.ListField(
        child=FirebaseDeviceDataSerializer(),
        min_length=1
    )
    save_to_db = serializers.BooleanField(default=False)

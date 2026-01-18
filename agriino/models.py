from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Device(models.Model):
    """
    Represents a sensor device that collects agricultural data from Firebase.
    """
    device_id = models.CharField(max_length=100, unique=True, help_text="Unique identifier from Firebase")
    name = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.FloatField(help_text="Device latitude coordinate")
    longitude = models.FloatField(help_text="Device longitude coordinate")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Device'
        verbose_name_plural = 'Devices'

    def __str__(self):
        return f"{self.name or self.device_id} ({self.latitude}, {self.longitude})"


class DeviceData(models.Model):
    """
    Stores the raw data received from Firebase for each device.
    """
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='data_points')
    
    # Sensor readings
    nitrogen = models.FloatField(help_text="Nitrogen value")
    spad = models.FloatField(null=True, blank=True, help_text="SPAD value")
    
    # RGB and color values
    a_rgb = models.FloatField(null=True, blank=True)
    a_r = models.FloatField(null=True, blank=True)
    a_g = models.FloatField(null=True, blank=True)
    a_b = models.FloatField(null=True, blank=True)
    r = models.FloatField(null=True, blank=True)
    g = models.FloatField(null=True, blank=True)
    b = models.FloatField(null=True, blank=True)
    o = models.FloatField(null=True, blank=True)
    v = models.FloatField(null=True, blank=True)
    y = models.FloatField(null=True, blank=True)
    
    # Transmittance values
    t_r = models.FloatField(null=True, blank=True)
    t_g = models.FloatField(null=True, blank=True)
    t_b = models.FloatField(null=True, blank=True)
    
    # Equation results
    eq1 = models.FloatField(null=True, blank=True)
    eq2 = models.FloatField(null=True, blank=True)
    class_eq1 = models.CharField(max_length=50, null=True, blank=True)
    class_eq2 = models.CharField(max_length=50, null=True, blank=True)
    
    # Timestamp from Firebase
    firebase_timestamp = models.BigIntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Device Data'
        verbose_name_plural = 'Device Data'

    def __str__(self):
        return f"Data for {self.device.device_id} - Nitrogen: {self.nitrogen}"


class Area(models.Model):
    """
    Represents a marked area on the map containing multiple devices.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Polygon coordinates stored as JSON (list of [lat, lng] pairs)
    polygon_coordinates = models.JSONField(
        default=list,
        help_text="List of [latitude, longitude] pairs defining the area boundary"
    )
    
    # Center point for the area
    center_latitude = models.FloatField(null=True, blank=True)
    center_longitude = models.FloatField(null=True, blank=True)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='areas'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Area'
        verbose_name_plural = 'Areas'

    def __str__(self):
        return self.name


class AreaDevice(models.Model):
    """
    Links devices to areas (many-to-many relationship with extra data).
    """
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='area_devices')
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='device_areas')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('area', 'device')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.device.device_id} in {self.area.name}"


class AnalysisResult(models.Model):
    """
    Stores the result of Kriging analysis for an area.
    """
    ANALYSIS_TYPE_CHOICES = [
        ('nitrogen', 'Nitrogen Analysis'),
        ('spad', 'SPAD Analysis'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='analysis_results')
    analysis_type = models.CharField(max_length=50, choices=ANALYSIS_TYPE_CHOICES, default='nitrogen')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Kriging parameters used
    variogram_model = models.CharField(max_length=50, default='spherical')
    nugget = models.FloatField(null=True, blank=True)
    sill = models.FloatField(null=True, blank=True)
    range_param = models.FloatField(null=True, blank=True)
    
    # Classification thresholds
    low_threshold = models.FloatField(default=1.5, help_text="Below this is LOW")
    high_threshold = models.FloatField(default=2.5, help_text="Above this is HIGH")
    
    # Summary statistics
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    mean_value = models.FloatField(null=True, blank=True)
    std_value = models.FloatField(null=True, blank=True)
    
    # Error message if failed
    error_message = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Analysis Result'
        verbose_name_plural = 'Analysis Results'

    def __str__(self):
        return f"{self.analysis_type} analysis for {self.area.name} - {self.status}"


class KrigingGrid(models.Model):
    """
    Stores the interpolated grid points from Kriging analysis.
    """
    CLASSIFICATION_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
    ]
    
    analysis_result = models.ForeignKey(
        AnalysisResult,
        on_delete=models.CASCADE,
        related_name='grid_points'
    )
    
    latitude = models.FloatField()
    longitude = models.FloatField()
    predicted_value = models.FloatField()
    variance = models.FloatField(null=True, blank=True, help_text="Kriging variance/uncertainty")
    classification = models.CharField(max_length=10, choices=CLASSIFICATION_CHOICES)

    class Meta:
        ordering = ['latitude', 'longitude']
        verbose_name = 'Kriging Grid Point'
        verbose_name_plural = 'Kriging Grid Points'

    def __str__(self):
        return f"({self.latitude}, {self.longitude}): {self.predicted_value} - {self.classification}"

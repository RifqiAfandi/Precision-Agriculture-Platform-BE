from django.contrib import admin
from .models import Device, Area, AreaDevice, AnalysisResult, KrigingGrid


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'name', 'latitude', 'longitude', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('device_id', 'name')
    ordering = ('-created_at',)


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name',)
    ordering = ('-created_at',)


@admin.register(AreaDevice)
class AreaDeviceAdmin(admin.ModelAdmin):
    list_display = ('area', 'device', 'added_at')
    list_filter = ('area', 'added_at')
    ordering = ('-added_at',)


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ('area', 'analysis_type', 'status', 'created_at')
    list_filter = ('analysis_type', 'status', 'created_at')
    search_fields = ('area__name',)
    ordering = ('-created_at',)


@admin.register(KrigingGrid)
class KrigingGridAdmin(admin.ModelAdmin):
    list_display = ('analysis_result', 'latitude', 'longitude', 'predicted_value', 'classification')
    list_filter = ('classification',)
    ordering = ('-analysis_result__created_at',)

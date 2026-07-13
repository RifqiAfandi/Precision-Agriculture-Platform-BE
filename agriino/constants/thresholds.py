"""
Nitrogen Classification Thresholds and Constants

This module contains all threshold values and constants used for
nitrogen level classification and Kriging analysis.

Classification Categories (based on nitrogen percentage):
- deficient: <1.80% (Red) - Needs immediate attention
- subnormal: 1.80-2.71% (Orange) - Below optimal
- normal: 2.71-3.31% (Yellow) - Optimal range
- high: >3.31% (Green) - Above optimal
"""

# =============================================================================
# NITROGEN CLASSIFICATION THRESHOLDS
# =============================================================================

# New 4-category threshold system
DEFAULT_DEFICIENT_THRESHOLD = 1.80  # Below this is DEFICIENT
DEFAULT_SUBNORMAL_THRESHOLD = 2.71  # Below this is SUBNORMAL (above deficient)
DEFAULT_NORMAL_THRESHOLD = 3.31     # Below this is NORMAL (above subnormal), above is HIGH

# Legacy thresholds for backward compatibility
DEFAULT_LOW_THRESHOLD = 1.80   # Same as deficient
DEFAULT_HIGH_THRESHOLD = 3.31  # Same as normal threshold

# Complete threshold configuration
NITROGEN_THRESHOLDS = {
    'deficient': {
        'max': DEFAULT_DEFICIENT_THRESHOLD,
        'label': 'Deficient',
        'label_id': 'Defisien',
        'description': 'Needs immediate nitrogen supplementation',
    },
    'subnormal': {
        'min': DEFAULT_DEFICIENT_THRESHOLD,
        'max': DEFAULT_SUBNORMAL_THRESHOLD,
        'label': 'Subnormal',
        'label_id': 'Subnormal',
        'description': 'Below optimal, consider fertilization',
    },
    'normal': {
        'min': DEFAULT_SUBNORMAL_THRESHOLD,
        'max': DEFAULT_NORMAL_THRESHOLD,
        'label': 'Normal',
        'label_id': 'Normal',
        'description': 'Optimal nitrogen levels',
    },
    'high': {
        'min': DEFAULT_NORMAL_THRESHOLD,
        'label': 'High',
        'label_id': 'Tinggi',
        'description': 'Above optimal, reduce fertilization',
    },
}


# =============================================================================
# CLASSIFICATION COLORS
# =============================================================================

CLASSIFICATION_COLORS = {
    'deficient': {
        'fill': '#E53935',
        'border': '#C62828',
        'bg_light': 'rgba(229, 57, 53, 0.2)',
    },
    'subnormal': {
        'fill': '#FB8C00',
        'border': '#EF6C00',
        'bg_light': 'rgba(251, 140, 0, 0.2)',
    },
    'normal': {
        'fill': '#FDD835',
        'border': '#F9A825',
        'bg_light': 'rgba(253, 216, 53, 0.2)',
    },
    'high': {
        'fill': '#43A047',
        'border': '#2E7D32',
        'bg_light': 'rgba(67, 160, 71, 0.2)',
    },
    'no_data': {
        'fill': '#9ca3af',
        'border': '#6b7280',
        'bg_light': 'rgba(156, 163, 175, 0.2)',
    },
    'unknown': {
        'fill': '#6b7280',
        'border': '#4b5563',
        'bg_light': 'rgba(107, 114, 128, 0.2)',
    },
}


# =============================================================================
# KRIGING ANALYSIS PARAMETERS
# =============================================================================

# Default influence radius in kilometers (0.03 km = 30 meters)
# Controls the area of influence around each device
DEFAULT_INFLUENCE_RADIUS_KM = 0.03

# Default grid resolution for Kriging interpolation
DEFAULT_GRID_RESOLUTION = 50

# Search neighborhood parameters for local Kriging
DEFAULT_MAX_NEIGHBORS = 12  # Maximum number of neighboring points
DEFAULT_MIN_NEIGHBORS = 3   # Minimum number of neighbors required

# Available variogram models
VARIOGRAM_MODELS = ['spherical', 'exponential', 'gaussian', 'linear']


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def classify_nitrogen_value(value: float) -> str:
    """
    Classify a nitrogen value based on thresholds.
    
    Args:
        value: Nitrogen percentage value
        
    Returns:
        Classification string: 'deficient', 'subnormal', 'normal', or 'high'
    """
    if value < DEFAULT_DEFICIENT_THRESHOLD:
        return 'deficient'
    elif value < DEFAULT_SUBNORMAL_THRESHOLD:
        return 'subnormal'
    elif value < DEFAULT_NORMAL_THRESHOLD:
        return 'normal'
    else:
        return 'high'


def get_classification_color(classification: str) -> dict:
    """
    Get color configuration for a classification.
    
    Args:
        classification: Classification string
        
    Returns:
        Dictionary with 'fill', 'border', and 'bg_light' color values
    """
    return CLASSIFICATION_COLORS.get(classification, CLASSIFICATION_COLORS['unknown'])

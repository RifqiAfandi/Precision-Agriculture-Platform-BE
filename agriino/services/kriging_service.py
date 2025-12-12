"""
Kriging Interpolation Service for Precision Agriculture

This module implements Ordinary Kriging for spatial interpolation of agricultural data,
specifically designed for nitrogen level analysis across farm areas.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from scipy.spatial.distance import cdist
from scipy.linalg import solve
import logging

logger = logging.getLogger(__name__)


@dataclass
class KrigingPoint:
    """Represents a point with coordinates and value."""
    latitude: float
    longitude: float
    value: float


@dataclass
class KrigingResult:
    """Represents the result of Kriging interpolation at a point."""
    latitude: float
    longitude: float
    predicted_value: float
    variance: float
    classification: str


class VariogramModel:
    """
    Variogram models for Kriging interpolation.
    
    Supports spherical, exponential, gaussian, and linear models.
    """
    
    @staticmethod
    def spherical(h: np.ndarray, nugget: float, sill: float, range_param: float) -> np.ndarray:
        """
        Spherical variogram model.
        
        γ(h) = nugget + sill * (1.5 * h/range - 0.5 * (h/range)^3) for h <= range
        γ(h) = nugget + sill for h > range
        """
        h = np.asarray(h)
        result = np.zeros_like(h, dtype=float)
        
        # For h > 0 and h <= range
        mask = (h > 0) & (h <= range_param)
        hr = h[mask] / range_param
        result[mask] = nugget + sill * (1.5 * hr - 0.5 * hr**3)
        
        # For h > range
        mask = h > range_param
        result[mask] = nugget + sill
        
        return result
    
    @staticmethod
    def exponential(h: np.ndarray, nugget: float, sill: float, range_param: float) -> np.ndarray:
        """
        Exponential variogram model.
        
        γ(h) = nugget + sill * (1 - exp(-3h/range))
        """
        h = np.asarray(h)
        result = np.zeros_like(h, dtype=float)
        mask = h > 0
        result[mask] = nugget + sill * (1 - np.exp(-3 * h[mask] / range_param))
        return result
    
    @staticmethod
    def gaussian(h: np.ndarray, nugget: float, sill: float, range_param: float) -> np.ndarray:
        """
        Gaussian variogram model.
        
        γ(h) = nugget + sill * (1 - exp(-(3h/range)^2))
        """
        h = np.asarray(h)
        result = np.zeros_like(h, dtype=float)
        mask = h > 0
        result[mask] = nugget + sill * (1 - np.exp(-(3 * h[mask] / range_param)**2))
        return result
    
    @staticmethod
    def linear(h: np.ndarray, nugget: float, sill: float, range_param: float) -> np.ndarray:
        """
        Linear variogram model with sill.
        
        γ(h) = nugget + (sill/range) * h for h <= range
        γ(h) = nugget + sill for h > range
        """
        h = np.asarray(h)
        result = np.zeros_like(h, dtype=float)
        
        mask = (h > 0) & (h <= range_param)
        result[mask] = nugget + (sill / range_param) * h[mask]
        
        mask = h > range_param
        result[mask] = nugget + sill
        
        return result


class KrigingService:
    """
    Ordinary Kriging interpolation service for agricultural data analysis.
    
    This service performs spatial interpolation of nitrogen (or other) values
    measured at specific device locations to predict values across an entire area.
    """
    
    # Classification thresholds for nitrogen levels
    DEFAULT_LOW_THRESHOLD = 1.5
    DEFAULT_HIGH_THRESHOLD = 2.5
    
    # Variogram models available
    VARIOGRAM_MODELS = {
        'spherical': VariogramModel.spherical,
        'exponential': VariogramModel.exponential,
        'gaussian': VariogramModel.gaussian,
        'linear': VariogramModel.linear,
    }
    
    def __init__(
        self,
        variogram_model: str = 'spherical',
        nugget: Optional[float] = None,
        sill: Optional[float] = None,
        range_param: Optional[float] = None,
        low_threshold: float = DEFAULT_LOW_THRESHOLD,
        high_threshold: float = DEFAULT_HIGH_THRESHOLD
    ):
        """
        Initialize the Kriging service.
        
        Args:
            variogram_model: Type of variogram model ('spherical', 'exponential', 'gaussian', 'linear')
            nugget: Nugget effect (discontinuity at origin). If None, will be estimated.
            sill: Sill value (plateau of variogram). If None, will be estimated.
            range_param: Range parameter (distance at which sill is reached). If None, will be estimated.
            low_threshold: Threshold below which nitrogen is classified as LOW
            high_threshold: Threshold above which nitrogen is classified as HIGH
        """
        if variogram_model not in self.VARIOGRAM_MODELS:
            raise ValueError(f"Unknown variogram model: {variogram_model}. "
                           f"Available models: {list(self.VARIOGRAM_MODELS.keys())}")
        
        self.variogram_model_name = variogram_model
        self.variogram_func = self.VARIOGRAM_MODELS[variogram_model]
        self.nugget = nugget
        self.sill = sill
        self.range_param = range_param
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold
        
        # Will be set after fitting
        self._fitted = False
        self._data_points: List[KrigingPoint] = []
        self._coordinates: Optional[np.ndarray] = None
        self._values: Optional[np.ndarray] = None
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the Haversine distance between two points on Earth.
        
        Returns distance in kilometers.
        """
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        
        a = np.sin(dlat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        
        return R * c
    
    def _calculate_distance_matrix(self, coords1: np.ndarray, coords2: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Calculate distance matrix between two sets of coordinates.
        
        Uses Haversine distance for geographic coordinates.
        """
        if coords2 is None:
            coords2 = coords1
        
        n1 = len(coords1)
        n2 = len(coords2)
        distances = np.zeros((n1, n2))
        
        for i in range(n1):
            for j in range(n2):
                distances[i, j] = self._haversine_distance(
                    coords1[i, 0], coords1[i, 1],
                    coords2[j, 0], coords2[j, 1]
                )
        
        return distances
    
    def _estimate_variogram_parameters(self, coordinates: np.ndarray, values: np.ndarray) -> Tuple[float, float, float]:
        """
        Estimate variogram parameters using Method of Moments.
        
        Returns:
            Tuple of (nugget, sill, range)
        """
        n = len(values)
        if n < 3:
            # Default parameters for small datasets
            variance = np.var(values) if len(values) > 1 else 1.0
            return 0.0, variance, 0.5
        
        # Calculate experimental variogram
        distances = self._calculate_distance_matrix(coordinates)
        
        # Get unique distances and bin them
        max_dist = np.max(distances) / 2  # Use half the maximum distance
        n_bins = min(10, n)
        bin_edges = np.linspace(0, max_dist, n_bins + 1)
        
        gamma_values = []
        lag_values = []
        
        for k in range(n_bins):
            mask = (distances > bin_edges[k]) & (distances <= bin_edges[k + 1])
            if np.sum(mask) > 0:
                pairs_i, pairs_j = np.where(mask)
                semivariance = 0.5 * np.mean((values[pairs_i] - values[pairs_j])**2)
                lag = (bin_edges[k] + bin_edges[k + 1]) / 2
                gamma_values.append(semivariance)
                lag_values.append(lag)
        
        if len(gamma_values) < 2:
            # Fallback to simple estimates
            variance = np.var(values)
            return 0.0, variance, max_dist
        
        gamma_values = np.array(gamma_values)
        lag_values = np.array(lag_values)
        
        # Estimate parameters
        nugget = max(0, gamma_values[0] * 0.1)  # Small nugget
        sill = np.max(gamma_values) - nugget
        
        # Estimate range as distance where variogram reaches ~95% of sill
        threshold = nugget + 0.95 * sill
        range_indices = np.where(gamma_values >= threshold)[0]
        if len(range_indices) > 0:
            range_param = lag_values[range_indices[0]]
        else:
            range_param = max_dist
        
        return nugget, max(sill, 0.001), max(range_param, 0.001)
    
    def fit(self, data_points: List[Dict]) -> 'KrigingService':
        """
        Fit the Kriging model to the data points.
        
        Args:
            data_points: List of dictionaries with 'latitude', 'longitude', and 'nitrogen' keys
            
        Returns:
            self for method chaining
        """
        if len(data_points) < 1:
            raise ValueError("At least 1 data point is required for Kriging")
        
        self._data_points = [
            KrigingPoint(
                latitude=p['latitude'],
                longitude=p['longitude'],
                value=p['nitrogen']
            )
            for p in data_points
        ]
        
        self._coordinates = np.array([
            [p.latitude, p.longitude] for p in self._data_points
        ])
        self._values = np.array([p.value for p in self._data_points])
        
        # Estimate variogram parameters if not provided
        if self.nugget is None or self.sill is None or self.range_param is None:
            est_nugget, est_sill, est_range = self._estimate_variogram_parameters(
                self._coordinates, self._values
            )
            self.nugget = self.nugget if self.nugget is not None else est_nugget
            self.sill = self.sill if self.sill is not None else est_sill
            self.range_param = self.range_param if self.range_param is not None else est_range
        
        logger.info(f"Fitted Kriging model with nugget={self.nugget:.4f}, "
                   f"sill={self.sill:.4f}, range={self.range_param:.4f}")
        
        self._fitted = True
        return self
    
    def _classify_value(self, value: float) -> str:
        """Classify a nitrogen value as low, normal, or high."""
        if value < self.low_threshold:
            return 'low'
        elif value > self.high_threshold:
            return 'high'
        else:
            return 'normal'
    
    def predict(self, target_points: List[Tuple[float, float]]) -> List[KrigingResult]:
        """
        Predict values at target points using Ordinary Kriging.
        
        Args:
            target_points: List of (latitude, longitude) tuples
            
        Returns:
            List of KrigingResult objects
        """
        if not self._fitted:
            raise RuntimeError("Model must be fitted before prediction. Call fit() first.")
        
        n = len(self._coordinates)
        
        # Handle single point case
        if n == 1:
            return [
                KrigingResult(
                    latitude=lat,
                    longitude=lon,
                    predicted_value=self._values[0],
                    variance=self.sill,
                    classification=self._classify_value(self._values[0])
                )
                for lat, lon in target_points
            ]
        
        # Build the Kriging matrix for known points
        dist_matrix = self._calculate_distance_matrix(self._coordinates)
        gamma_matrix = self.variogram_func(dist_matrix, self.nugget, self.sill, self.range_param)
        
        # Add Lagrange multiplier row and column
        K = np.zeros((n + 1, n + 1))
        K[:n, :n] = gamma_matrix
        K[n, :n] = 1
        K[:n, n] = 1
        K[n, n] = 0
        
        results = []
        
        for lat, lon in target_points:
            target_coord = np.array([[lat, lon]])
            
            # Calculate distances to target
            dist_to_target = self._calculate_distance_matrix(self._coordinates, target_coord).flatten()
            gamma_to_target = self.variogram_func(dist_to_target, self.nugget, self.sill, self.range_param)
            
            # Right-hand side vector
            k = np.zeros(n + 1)
            k[:n] = gamma_to_target
            k[n] = 1
            
            try:
                # Solve the Kriging system
                weights = solve(K, k, assume_a='sym')
                
                # Predicted value
                predicted_value = np.sum(weights[:n] * self._values)
                
                # Kriging variance
                variance = np.sum(weights[:n] * gamma_to_target) + weights[n]
                variance = max(0, variance)  # Ensure non-negative
                
            except np.linalg.LinAlgError:
                # Fallback to IDW-like interpolation
                logger.warning("Kriging system singular, using IDW fallback")
                
                if np.min(dist_to_target) < 1e-10:
                    idx = np.argmin(dist_to_target)
                    predicted_value = self._values[idx]
                    variance = 0
                else:
                    weights = 1 / (dist_to_target ** 2)
                    weights /= np.sum(weights)
                    predicted_value = np.sum(weights * self._values)
                    variance = self.sill
            
            results.append(KrigingResult(
                latitude=lat,
                longitude=lon,
                predicted_value=float(predicted_value),
                variance=float(variance),
                classification=self._classify_value(predicted_value)
            ))
        
        return results
    
    def generate_grid(
        self,
        bounds: Dict[str, float],
        resolution: int = 20
    ) -> List[KrigingResult]:
        """
        Generate a grid of predictions within the specified bounds.
        
        Args:
            bounds: Dictionary with 'min_lat', 'max_lat', 'min_lng', 'max_lng'
            resolution: Number of points along each axis
            
        Returns:
            List of KrigingResult objects for the grid
        """
        lat_range = np.linspace(bounds['min_lat'], bounds['max_lat'], resolution)
        lng_range = np.linspace(bounds['min_lng'], bounds['max_lng'], resolution)
        
        target_points = [
            (lat, lng)
            for lat in lat_range
            for lng in lng_range
        ]
        
        return self.predict(target_points)
    
    def get_statistics(self, results: List[KrigingResult]) -> Dict:
        """
        Calculate summary statistics for the Kriging results.
        
        Args:
            results: List of KrigingResult objects
            
        Returns:
            Dictionary with statistics
        """
        values = [r.predicted_value for r in results]
        classifications = [r.classification for r in results]
        
        return {
            'min_value': float(np.min(values)),
            'max_value': float(np.max(values)),
            'mean_value': float(np.mean(values)),
            'std_value': float(np.std(values)),
            'low_count': classifications.count('low'),
            'normal_count': classifications.count('normal'),
            'high_count': classifications.count('high'),
            'total_points': len(results),
            'variogram_model': self.variogram_model_name,
            'nugget': self.nugget,
            'sill': self.sill,
            'range': self.range_param,
        }


def analyze_nitrogen_levels(
    device_data: List[Dict],
    grid_bounds: Optional[Dict[str, float]] = None,
    grid_resolution: int = 20,
    variogram_model: str = 'spherical',
    low_threshold: float = 1.5,
    high_threshold: float = 2.5
) -> Dict:
    """
    Main function to analyze nitrogen levels using Kriging interpolation.
    
    Args:
        device_data: List of device data dictionaries with lat, lng, and nitrogen values
        grid_bounds: Optional bounds for grid generation. If None, calculated from data.
        grid_resolution: Number of grid points per axis
        variogram_model: Variogram model to use
        low_threshold: Nitrogen threshold for LOW classification
        high_threshold: Nitrogen threshold for HIGH classification
        
    Returns:
        Dictionary with analysis results including:
        - grid_points: List of interpolated points with classifications
        - statistics: Summary statistics
        - input_points: Original data points with classifications
        - variogram_params: Estimated variogram parameters
    """
    if not device_data:
        raise ValueError("No device data provided for analysis")
    
    # Initialize and fit the Kriging service
    kriging = KrigingService(
        variogram_model=variogram_model,
        low_threshold=low_threshold,
        high_threshold=high_threshold
    )
    kriging.fit(device_data)
    
    # Calculate bounds if not provided
    if grid_bounds is None:
        lats = [d['latitude'] for d in device_data]
        lngs = [d['longitude'] for d in device_data]
        
        # Add some padding (approximately 100 meters)
        padding = 0.001  # About 100m in decimal degrees
        grid_bounds = {
            'min_lat': min(lats) - padding,
            'max_lat': max(lats) + padding,
            'min_lng': min(lngs) - padding,
            'max_lng': max(lngs) + padding,
        }
    
    # Generate grid predictions
    grid_results = kriging.generate_grid(grid_bounds, grid_resolution)
    
    # Get statistics
    statistics = kriging.get_statistics(grid_results)
    
    # Classify input points
    input_results = kriging.predict([
        (d['latitude'], d['longitude']) for d in device_data
    ])
    
    return {
        'grid_points': [
            {
                'latitude': r.latitude,
                'longitude': r.longitude,
                'predicted_value': r.predicted_value,
                'variance': r.variance,
                'classification': r.classification,
            }
            for r in grid_results
        ],
        'statistics': statistics,
        'input_points': [
            {
                'latitude': device_data[i]['latitude'],
                'longitude': device_data[i]['longitude'],
                'nitrogen': device_data[i]['nitrogen'],
                'predicted_value': input_results[i].predicted_value,
                'classification': input_results[i].classification,
            }
            for i in range(len(device_data))
        ],
        'variogram_params': {
            'model': variogram_model,
            'nugget': kriging.nugget,
            'sill': kriging.sill,
            'range': kriging.range_param,
        },
        'bounds': grid_bounds,
        'thresholds': {
            'low': low_threshold,
            'high': high_threshold,
        }
    }

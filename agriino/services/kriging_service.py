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
    
    Features:
    - Influence radius: Only areas within the radius of sensors show interpolated values
    - Areas outside influence radius are marked as 'no_data' (neutral/gray)
    - Each sensor has a configurable influence radius
    """
    
    # Classification thresholds for nitrogen levels (based on actual nitrogen percentage)
    # deficient: <1.80%
    # subnormal: 1.80 - 2.71%
    # normal: 2.71 - 3.31%
    # high: >3.31%
    DEFAULT_DEFICIENT_THRESHOLD = 1.80
    DEFAULT_SUBNORMAL_THRESHOLD = 2.71
    DEFAULT_NORMAL_THRESHOLD = 3.31
    
    # Legacy thresholds for backward compatibility
    DEFAULT_LOW_THRESHOLD = 1.80
    DEFAULT_HIGH_THRESHOLD = 3.31
    
    # Default influence radius in kilometers (0.05 km = 50 meters)
    DEFAULT_INFLUENCE_RADIUS = 0.05
    
    # Search neighborhood defaults
    DEFAULT_MAX_NEIGHBORS = 12
    DEFAULT_MIN_NEIGHBORS = 3
    
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
        high_threshold: float = DEFAULT_HIGH_THRESHOLD,
        influence_radius: float = DEFAULT_INFLUENCE_RADIUS,
        deficient_threshold: float = DEFAULT_DEFICIENT_THRESHOLD,
        subnormal_threshold: float = DEFAULT_SUBNORMAL_THRESHOLD,
        normal_threshold: float = DEFAULT_NORMAL_THRESHOLD,
        max_neighbors: int = DEFAULT_MAX_NEIGHBORS,
        min_neighbors: int = DEFAULT_MIN_NEIGHBORS
    ):
        """
        Initialize the Kriging service.
        
        Args:
            variogram_model: Type of variogram model ('spherical', 'exponential', 'gaussian', 'linear')
            nugget: Nugget effect (discontinuity at origin). If None, will be estimated.
            sill: Sill value (plateau of variogram). If None, will be estimated.
            range_param: Range parameter (distance at which sill is reached). If None, will be estimated.
            low_threshold: Threshold below which nitrogen is classified as LOW (legacy)
            high_threshold: Threshold above which nitrogen is classified as HIGH (legacy)
            influence_radius: Maximum distance (in km) from a sensor for interpolation to apply
            deficient_threshold: Threshold below which nitrogen is classified as DEFICIENT (<1.80%)
            subnormal_threshold: Threshold for SUBNORMAL classification (1.80-2.71%)
            normal_threshold: Threshold for NORMAL classification (2.71-3.31%), above is HIGH
            max_neighbors: Maximum number of neighboring points for local kriging (search neighborhood)
            min_neighbors: Minimum number of neighbors required for a valid prediction
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
        self.influence_radius = influence_radius
        
        # New threshold system
        self.deficient_threshold = deficient_threshold
        self.subnormal_threshold = subnormal_threshold
        self.normal_threshold = normal_threshold
        
        # Search neighborhood parameters
        self.max_neighbors = max_neighbors
        self.min_neighbors = min_neighbors
        
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
        Estimate variogram parameters using Method of Moments with improved estimation.
        
        This implementation addresses common issues in variogram fitting:
        1. Uses robust binning with sufficient lag classes
        2. Properly estimates nugget from short-distance pairs
        3. Uses weighted least squares fitting for range estimation
        4. Handles small sample sizes gracefully
        
        Returns:
            Tuple of (nugget, sill, range)
        """
        n = len(values)
        variance = np.var(values) if n > 1 else 1.0
        
        if n < 3:
            # Default parameters for small datasets
            # Use a range that's approximately 1/3 of the study area extent
            # This ensures localized influence
            return 0.0, max(variance, 0.001), 0.02  # 20 meters default range
        
        # Calculate experimental variogram
        distances = self._calculate_distance_matrix(coordinates)
        
        # Get all unique non-zero distances
        upper_tri_indices = np.triu_indices(n, k=1)
        all_distances = distances[upper_tri_indices]
        
        if len(all_distances) == 0:
            return 0.0, max(variance, 0.001), 0.02
        
        # Use maximum lag distance as 60% of max distance (Journel & Huijbregts recommendation)
        # This avoids unreliable estimates at large lags
        max_lag = np.max(all_distances) * 0.6
        min_lag = np.min(all_distances[all_distances > 0]) if np.any(all_distances > 0) else 0.001
        
        # Determine optimal number of bins based on data
        # Use Sturges' rule with minimum of 8 and maximum of 15 bins
        n_pairs = len(all_distances)
        n_bins = max(8, min(15, int(1 + 3.322 * np.log10(n_pairs))))
        
        # Create bins with equal spacing
        bin_edges = np.linspace(0, max_lag, n_bins + 1)
        
        gamma_values = []
        lag_values = []
        pair_counts = []
        
        for k in range(n_bins):
            mask = (distances > bin_edges[k]) & (distances <= bin_edges[k + 1])
            count = np.sum(mask)
            if count >= 1:  # Need at least 1 pair per bin (ideally more)
                pairs_i, pairs_j = np.where(mask)
                semivariance = 0.5 * np.mean((values[pairs_i] - values[pairs_j])**2)
                lag = (bin_edges[k] + bin_edges[k + 1]) / 2
                gamma_values.append(semivariance)
                lag_values.append(lag)
                pair_counts.append(count)
        
        if len(gamma_values) < 2:
            # Fallback: use data variance and reasonable range
            return 0.0, max(variance, 0.001), max_lag / 3
        
        gamma_values = np.array(gamma_values)
        lag_values = np.array(lag_values)
        pair_counts = np.array(pair_counts)
        
        # Estimate nugget: extrapolate from first few bins to h=0
        # Use weighted linear regression on first 3 bins (or fewer if not available)
        n_for_nugget = min(3, len(gamma_values))
        if n_for_nugget >= 2:
            # Simple linear extrapolation to h=0
            slope = (gamma_values[n_for_nugget-1] - gamma_values[0]) / (lag_values[n_for_nugget-1] - lag_values[0] + 1e-10)
            nugget = max(0, gamma_values[0] - slope * lag_values[0])
        else:
            nugget = gamma_values[0] * 0.5
        
        # Ensure nugget is reasonable (typically 0-50% of sill)
        nugget = min(nugget, variance * 0.5)
        nugget = max(nugget, 0.0)
        
        # Estimate sill as the asymptotic variance
        # Use weighted average of values in the plateau region
        sill_candidates = gamma_values[gamma_values >= np.percentile(gamma_values, 70)]
        if len(sill_candidates) > 0:
            total_sill = np.mean(sill_candidates)
        else:
            total_sill = np.max(gamma_values)
        
        # Partial sill (sill above nugget)
        partial_sill = max(total_sill - nugget, 0.001)
        
        # Estimate range using weighted least squares fit
        # Find where variogram reaches ~63% of sill (characteristic range for exponential)
        # or ~86% for spherical model effective range
        if self.variogram_model_name == 'exponential':
            target_gamma = nugget + 0.632 * partial_sill  # 1 - e^(-1)
        elif self.variogram_model_name == 'gaussian':
            target_gamma = nugget + 0.632 * partial_sill  # Similar behavior
        else:  # spherical, linear
            target_gamma = nugget + 0.5 * partial_sill  # 50% of sill
        
        # Find range by interpolation
        range_param = None
        for i in range(len(gamma_values) - 1):
            if gamma_values[i] <= target_gamma <= gamma_values[i + 1]:
                # Linear interpolation
                t = (target_gamma - gamma_values[i]) / (gamma_values[i + 1] - gamma_values[i] + 1e-10)
                range_param = lag_values[i] + t * (lag_values[i + 1] - lag_values[i])
                break
        
        if range_param is None:
            if gamma_values[0] >= target_gamma:
                # All values above target, use first lag
                range_param = lag_values[0]
            else:
                # Variogram hasn't reached sill, use 2/3 of max lag
                range_param = max_lag * 0.67
        
        # Ensure range is reasonable for agricultural applications
        # Minimum range: ~5 meters (0.005 km)
        # Maximum range: max_lag (60% of study area)
        range_param = max(range_param, 0.005)
        range_param = min(range_param, max_lag)
        
        logger.debug(f"Variogram estimation: nugget={nugget:.6f}, sill={partial_sill:.6f}, range={range_param:.6f}")
        logger.debug(f"Experimental variogram lags: {lag_values}")
        logger.debug(f"Experimental variogram values: {gamma_values}")
        
        return nugget, max(partial_sill, 0.001), max(range_param, 0.001)
    
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
    
    def _classify_value(self, value: float, is_within_influence: bool = True) -> str:
        """
        Classify a nitrogen value based on thresholds.
        
        Categories (based on nitrogen percentage):
        - deficient: <1.80% (Red)
        - subnormal: 1.80-2.71% (Dark Orange)
        - normal: 2.71-3.31% (Light Orange)
        - high: >3.31% (Yellow)
        - no_data: outside influence radius (Gray/Neutral)
        
        Args:
            value: Nitrogen value to classify
            is_within_influence: Whether the point is within sensor influence radius
            
        Returns:
            Classification string
        """
        if not is_within_influence:
            return 'no_data'
        
        if value < self.deficient_threshold:
            return 'deficient'
        elif value < self.subnormal_threshold:
            return 'subnormal'
        elif value < self.normal_threshold:
            return 'normal'
        else:
            return 'high'
    
    def predict(self, target_points: List[Tuple[float, float]]) -> List[KrigingResult]:
        """
        Predict values at target points using Ordinary Kriging with local neighborhood.
        
        This implementation uses a search neighborhood approach for local kriging,
        which provides better local influence and more realistic spatial patterns:
        1. For each target point, find the nearest neighbors within influence radius
        2. Use only those neighbors for kriging (local kriging)
        3. This preserves point-level variability and localized influence
        
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
            results = []
            for lat, lon in target_points:
                # Check if within influence radius
                dist = self._haversine_distance(
                    lat, lon,
                    self._coordinates[0][0], self._coordinates[0][1]
                )
                is_within = dist <= self.influence_radius
                
                results.append(KrigingResult(
                    latitude=lat,
                    longitude=lon,
                    predicted_value=self._values[0] if is_within else 0.0,
                    variance=self.sill,
                    classification=self._classify_value(self._values[0], is_within)
                ))
            return results
        
        results = []
        
        for lat, lon in target_points:
            target_coord = np.array([[lat, lon]])
            
            # Calculate distances from target to all data points
            dist_to_target = self._calculate_distance_matrix(self._coordinates, target_coord).flatten()
            
            # Find points within influence radius
            within_radius_mask = dist_to_target <= self.influence_radius
            within_radius_indices = np.where(within_radius_mask)[0]
            
            # Check if point is within influence radius of any sensor
            min_distance = np.min(dist_to_target)
            is_within_influence = min_distance <= self.influence_radius
            
            if not is_within_influence or len(within_radius_indices) < self.min_neighbors:
                # Not enough neighbors or outside influence radius
                results.append(KrigingResult(
                    latitude=lat,
                    longitude=lon,
                    predicted_value=0.0,
                    variance=float(self.sill),
                    classification='no_data'
                ))
                continue
            
            # Select neighbors for local kriging
            # Sort by distance and take up to max_neighbors
            sorted_indices = np.argsort(dist_to_target)
            neighbor_indices = []
            for idx in sorted_indices:
                if dist_to_target[idx] <= self.influence_radius:
                    neighbor_indices.append(idx)
                    if len(neighbor_indices) >= self.max_neighbors:
                        break
            
            neighbor_indices = np.array(neighbor_indices)
            n_neighbors = len(neighbor_indices)
            
            if n_neighbors < self.min_neighbors:
                # Fall back to using closest neighbors even if outside radius
                neighbor_indices = sorted_indices[:self.min_neighbors]
                n_neighbors = len(neighbor_indices)
            
            # Extract neighbor coordinates and values
            neighbor_coords = self._coordinates[neighbor_indices]
            neighbor_values = self._values[neighbor_indices]
            neighbor_distances = dist_to_target[neighbor_indices]
            
            # Build local kriging matrix for selected neighbors
            local_dist_matrix = self._calculate_distance_matrix(neighbor_coords)
            local_gamma_matrix = self.variogram_func(local_dist_matrix, self.nugget, self.sill, self.range_param)
            
            # Add Lagrange multiplier row and column for unbiasedness constraint
            K = np.zeros((n_neighbors + 1, n_neighbors + 1))
            K[:n_neighbors, :n_neighbors] = local_gamma_matrix
            K[n_neighbors, :n_neighbors] = 1
            K[:n_neighbors, n_neighbors] = 1
            K[n_neighbors, n_neighbors] = 0
            
            # Right-hand side: gamma values from target to neighbors
            gamma_to_target = self.variogram_func(neighbor_distances, self.nugget, self.sill, self.range_param)
            k = np.zeros(n_neighbors + 1)
            k[:n_neighbors] = gamma_to_target
            k[n_neighbors] = 1
            
            try:
                # Add small regularization to diagonal to prevent singularity
                # This is a standard technique for ill-conditioned kriging systems
                regularization = 1e-10 * self.sill
                np.fill_diagonal(K[:n_neighbors, :n_neighbors], 
                               np.diag(K[:n_neighbors, :n_neighbors]) + regularization)
                
                # Solve the Kriging system
                weights = solve(K, k, assume_a='sym')
                
                # Predicted value (sum of weights * values)
                predicted_value = np.sum(weights[:n_neighbors] * neighbor_values)
                
                # Kriging variance
                variance = np.sum(weights[:n_neighbors] * gamma_to_target) + weights[n_neighbors]
                variance = max(0, variance)  # Ensure non-negative
                
            except np.linalg.LinAlgError:
                # Fallback to IDW interpolation
                logger.warning("Local Kriging system singular, using IDW fallback")
                
                if np.min(neighbor_distances) < 1e-10:
                    idx = np.argmin(neighbor_distances)
                    predicted_value = neighbor_values[idx]
                    variance = 0
                else:
                    # IDW with squared distance weights
                    idw_weights = 1 / (neighbor_distances ** 2)
                    idw_weights /= np.sum(idw_weights)
                    predicted_value = np.sum(idw_weights * neighbor_values)
                    variance = self.sill
            
            results.append(KrigingResult(
                latitude=lat,
                longitude=lon,
                predicted_value=float(predicted_value),
                variance=float(variance),
                classification=self._classify_value(predicted_value, is_within_influence)
            ))
        
        return results
    
    def generate_grid(
        self,
        bounds: Dict[str, float],
        resolution: int = 50
    ) -> List[KrigingResult]:
        """
        Generate a grid of predictions within the specified bounds.
        
        Args:
            bounds: Dictionary with 'min_lat', 'max_lat', 'min_lng', 'max_lng'
            resolution: Number of points along each axis (default 50 for smoother output)
            
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
        # Filter out no_data points for value calculations
        data_results = [r for r in results if r.classification != 'no_data']
        
        if data_results:
            values = [r.predicted_value for r in data_results]
            min_val = float(np.min(values))
            max_val = float(np.max(values))
            mean_val = float(np.mean(values))
            std_val = float(np.std(values))
        else:
            min_val = max_val = mean_val = std_val = 0.0
        
        classifications = [r.classification for r in results]
        
        return {
            'min_value': min_val,
            'max_value': max_val,
            'mean_value': mean_val,
            'std_value': std_val,
            # New 4-category classification counts
            'deficient_count': classifications.count('deficient'),
            'subnormal_count': classifications.count('subnormal'),
            'normal_count': classifications.count('normal'),
            'high_count': classifications.count('high'),
            'no_data_count': classifications.count('no_data'),
            # Legacy counts for backward compatibility
            'low_count': classifications.count('deficient') + classifications.count('subnormal'),
            'total_points': len(results),
            'data_points': len(data_results),
            'variogram_model': self.variogram_model_name,
            'nugget': self.nugget,
            'sill': self.sill,
            'range': self.range_param,
            'influence_radius': self.influence_radius,
        }


def analyze_nitrogen_levels(
    device_data: List[Dict],
    grid_bounds: Optional[Dict[str, float]] = None,
    grid_resolution: int = 50,
    variogram_model: str = 'spherical',
    low_threshold: float = 1.80,
    high_threshold: float = 3.31,
    influence_radius: float = 0.05,
    deficient_threshold: float = 1.80,
    subnormal_threshold: float = 2.71,
    normal_threshold: float = 3.31,
    max_neighbors: int = 12,
    min_neighbors: int = 3
) -> Dict:
    """
    Main function to analyze nitrogen levels using Kriging interpolation.
    
    Args:
        device_data: List of device data dictionaries with lat, lng, and nitrogen values
        grid_bounds: Optional bounds for grid generation. If None, calculated from data.
        grid_resolution: Number of grid points per axis (default 50 for smoother output)
        variogram_model: Variogram model to use
        low_threshold: Nitrogen threshold for LOW classification (legacy)
        high_threshold: Nitrogen threshold for HIGH classification (legacy)
        influence_radius: Maximum distance (in km) from sensors for interpolation (default 50m)
        deficient_threshold: Threshold for DEFICIENT classification (<1.80%)
        subnormal_threshold: Threshold for SUBNORMAL classification (1.80-2.71%)
        normal_threshold: Threshold for NORMAL classification (2.71-3.31%), above is HIGH
        max_neighbors: Maximum number of neighboring points to use in kriging (search neighborhood)
        min_neighbors: Minimum number of neighbors required for valid prediction
        
    Returns:
        Dictionary with analysis results including:
        - grid_points: List of interpolated points with classifications
        - statistics: Summary statistics
        - input_points: Original data points with classifications
        - variogram_params: Estimated variogram parameters
    """
        deficient_threshold: Threshold for DEFICIENT classification (<1.80%)
        subnormal_threshold: Threshold for SUBNORMAL classification (1.80-2.71%)
        normal_threshold: Threshold for NORMAL classification (2.71-3.31%), above is HIGH
        max_neighbors: Maximum number of neighboring points to use in kriging (search neighborhood)
        min_neighbors: Minimum number of neighbors required for valid prediction
        
    Returns:
        Dictionary with analysis results including:
        - grid_points: List of interpolated points with classifications
        - statistics: Summary statistics
        - input_points: Original data points with classifications
        - variogram_params: Estimated variogram parameters
    """
    if not device_data:
        raise ValueError("No device data provided for analysis")
    
    # Initialize and fit the Kriging service with parameters
    kriging = KrigingService(
        variogram_model=variogram_model,
        low_threshold=low_threshold,
        high_threshold=high_threshold,
        influence_radius=influence_radius,
        deficient_threshold=deficient_threshold,
        subnormal_threshold=subnormal_threshold,
        normal_threshold=normal_threshold,
        max_neighbors=max_neighbors,
        min_neighbors=min_neighbors
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
            'influence_radius': influence_radius,
        },
        'bounds': grid_bounds,
        'thresholds': {
            'low': low_threshold,
            'high': high_threshold,
            'deficient': deficient_threshold,
            'subnormal': subnormal_threshold,
            'normal': normal_threshold,
        }
    }

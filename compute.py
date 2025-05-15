"""
Computation module: Implements cruising speed calculation logic
"""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

import config
from models import RideData


class CruisingSpeedCalculator:
    """Cruising speed calculator"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the calculator

        Args:
            config (Dict[str, Any], optional): Configuration parameters
        """
        self.config = config if config is not None else {}

    def calculate(self, data: RideData) -> Dict[str, Any]:
        """
        Calculate cruising speed and related metrics

        Args:
            data (RideData): Processed data

        Returns:
            Dict[str, Any]: Calculation results, including cruising speed and other metrics
        """
        df = data.to_dataframe()

        # Extract cruising data
        cruising_data = df[df['is_cruising']].copy()

        if cruising_data.empty:
            print("Warning: No cruising data segments identified with current thresholds.")
            self._print_debug_info(df)
            return {
                'cruising_speed': None,
                'success': False,
                'message': 'No cruising data identified'
            }

        # Calculate total cruising time
        cruising_total_time_seconds = cruising_data['time_diff_seconds'].sum()

        if cruising_total_time_seconds <= 0:
            print("Warning: Total cruising time is zero or negative, cannot calculate weighted average speed.")
            return {
                'cruising_speed': None,
                'avg_speed': cruising_data['speed_kmh'].mean() if not cruising_data.empty else None,
                'success': False,
                'message': 'Abnormal total cruising time'
            }

        # Calculate time-weighted cruising speed
        weighted_cruising_speed_kmh = (
            cruising_data['speed_kmh'] * cruising_data['time_diff_seconds']
        ).sum() / cruising_total_time_seconds

        # Prepare results
        result = {
            'cruising_speed': weighted_cruising_speed_kmh,
            'avg_speed': cruising_data['speed_kmh'].mean(),
            'cruising_points': len(cruising_data),
            'total_points': len(df),
            'cruising_time_seconds': cruising_total_time_seconds,
            'success': True
        }

        # Add optional metrics
        self._add_optional_metrics(result, cruising_data, cruising_total_time_seconds)

        return result

    def _add_optional_metrics(self, result: Dict[str, Any],
                             cruising_data: pd.DataFrame,
                             cruising_total_time_seconds: float) -> None:
        """Add optional calculated metrics (e.g., power, cadence)"""

        # Calculate average cruising power (if available)
        if 'power' in cruising_data.columns and cruising_data['power'].notna().any():
            result['avg_power'] = (
                cruising_data['power'] * cruising_data['time_diff_seconds']
            ).sum() / cruising_total_time_seconds

        # Calculate average cruising cadence (if available)
        if 'cadence' in cruising_data.columns and cruising_data['cadence'].notna().any():
            result['avg_cadence'] = (
                cruising_data['cadence'] * cruising_data['time_diff_seconds']
            ).sum() / cruising_total_time_seconds

        # Calculate average cruising heart rate (if available)
        if 'heart_rate' in cruising_data.columns and cruising_data['heart_rate'].notna().any():
            result['avg_heart_rate'] = (
                cruising_data['heart_rate'] * cruising_data['time_diff_seconds']
            ).sum() / cruising_total_time_seconds

    def _print_debug_info(self, df: pd.DataFrame) -> None:
        """Print debug information"""
        print("\nData overview (for threshold debugging):")
        print(f"  Overall average speed (km/h): {df['speed_kmh'].mean():.2f}")
        print(f"  Max speed (km/h): {df['speed_kmh'].max():.2f}")
        print(f"  Min speed (km/h): {df['speed_kmh'].min():.2f}")

        if not df[df['is_stopped']].empty:
            print(f"  Average speed of 'stopped' points (km/h): {df[df['is_stopped']]['speed_kmh'].mean():.2f}")

        print(f"  Maximum absolute acceleration (m/s^2): {df['acceleration'].abs().max():.2f}")

        if 'speed_rolling_std_kmh' in df.columns:
            print(f"  Maximum speed rolling standard deviation (km/h): {df['speed_rolling_std_kmh'].max():.2f}")

        if 'power' in df.columns and df['power'].notna().any():
            print(f"  Overall average power (W): {df['power'].mean():.2f}")
            print(f"  Max power (W): {df['power'].max():.2f}")
            print(f"  Min power (W): {df['power'].min():.2f}")


class NormalizedPowerCalculator:
    """Normalized Power (NP) calculator"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the calculator

        Args:
            config (Dict[str, Any], optional): Configuration parameters
        """
        self.config = config if config is not None else {}

    def calculate(self, data: RideData) -> Dict[str, Any]:
        """
        Calculate Normalized Power (NP) and related metrics

        Args:
            data (RideData): Processed ride data

        Returns:
            Dict[str, Any]: Calculation results, including NP and other metrics
        """
        df = data.to_dataframe()
        
        # Check if power data exists
        if 'power' not in df.columns or df['power'].isna().all():
            return {
                'normalized_power': None,
                'success': False,
                'message': 'No power data available'
            }
            
        # Get configuration parameters
        window_size = self.config.get('np_window_size_seconds', config.NP_WINDOW_SIZE_SECONDS)
        exponent = self.config.get('np_exponent', config.NP_EXPONENT)
        
        # Calculate time-weighted average power for reference
        if 'time_diff_seconds' in df.columns and df['time_diff_seconds'].sum() > 0:
            avg_power = (df['power'] * df['time_diff_seconds']).sum() / df['time_diff_seconds'].sum()
        else:
            avg_power = df['power'].mean()
            
        # Handle short rides
        if len(df) < window_size:
            return {
                'normalized_power': None, 
                'avg_power': avg_power,
                'success': False,
                'message': f'Ride too short for NP calculation (minimum {window_size}s)'
            }
            
        # Step 1: Calculate rolling average with specified window size
        mean_time_diff = df['time_diff_seconds'].mean() if 'time_diff_seconds' in df.columns else 1.0
        window_points = max(1, int(window_size / mean_time_diff))
        
        # Calculate rolling average power
        df['power_30s_avg'] = df['power'].rolling(
            window=window_points, 
            min_periods=1, 
            center=True
        ).mean()
        
        # Step 2: Raise to 4th power
        df['power_30s_avg_4th'] = df['power_30s_avg'] ** exponent
        
        # Step 3: Calculate average of 4th power values
        avg_4th_power = df['power_30s_avg_4th'].mean()
        
        # Step 4: Take 4th root
        normalized_power = avg_4th_power ** (1/exponent)
        
        # Calculate Intensity Factor (IF) if FTP is available
        intensity_factor = None
        if 'ftp' in self.config and self.config['ftp'] is not None and self.config['ftp'] > 0:
            intensity_factor = normalized_power / self.config['ftp']
            
        # Prepare results
        result = {
            'normalized_power': normalized_power,
            'avg_power': avg_power,
            'intensity_factor': intensity_factor,
            'np_to_avg_ratio': normalized_power / avg_power if avg_power > 0 else None,
            'success': True
        }
        
        return result


# Factory function to create different types of calculators
def create_calculator(calculator_type='cruising_speed', config=None):
    """
    Create a calculator instance

    Args:
        calculator_type (str): Type of calculator
        config (Dict[str, Any], optional): Configuration parameters

    Returns:
        Calculator instance
    """
    if calculator_type == 'cruising_speed':
        return CruisingSpeedCalculator(config)
    elif calculator_type == 'normalized_power':
        return NormalizedPowerCalculator(config)
    else:
        raise ValueError(f"Unsupported calculator type: {calculator_type}")
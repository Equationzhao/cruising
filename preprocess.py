"""
Preprocessing module: Provides a pluggable data preprocessing pipeline
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

import config
from models import RideData


class Processor(ABC):
    """Base data processor class, defines interface standards"""

    @abstractmethod
    def process(self, data: RideData, conf: Dict[str, Any]) -> RideData:
        """
        Process data

        Args:
            data (RideData): Data to be processed
            conf (Dict[str, Any]): Configuration parameters

        Returns:
            RideData: Processed data
        """
        pass

    @property
    def description(self) -> str:
        """Processor description"""
        return "Data Processor"


class ConvertSpeedToKmh(Processor):
    """Speed unit conversion processor: m/s → km/h"""

    def process(self, data: RideData, conf: Dict[str, Any]) -> RideData:
        """Convert speed from m/s to km/h"""
        for record in data.records:
            record.speed_kmh = record.speed * 3.6
        return data

    @property
    def description(self) -> str:
        return "Convert Speed: m/s → km/h"


class SortAndCalculateTimeDiff(Processor):
    """Sort by time and calculate time differences"""

    def process(self, data: RideData, conf: Dict[str, Any]) -> RideData:
        """Sort by timestamp and calculate time differences between consecutive records"""
        df = data.to_dataframe()

        # Sort by timestamp
        df = df.sort_values(by='timestamp').reset_index(drop=True)

        # Calculate time difference (seconds)
        df['time_diff_seconds'] = df['timestamp'].diff().dt.total_seconds()

        # Handle NaN for the first row's time difference
        if len(df) > 1 and pd.isna(df.loc[0, 'time_diff_seconds']):
            common_diff = df['time_diff_seconds'].median()
            df.loc[0, 'time_diff_seconds'] = common_diff if pd.notna(common_diff) and common_diff > 0 else 1.0

        # Calculate cumulative time
        df['cumulative_time_seconds'] = df['time_diff_seconds'].cumsum().fillna(0)

        return RideData.from_dataframe(df)

    @property
    def description(self) -> str:
        return "Sort and Calculate Time Differences"


class MarkStops(Processor):
    """Mark stop points"""

    def process(self, data: RideData, conf: Dict[str, Any]) -> RideData:
        """Mark stop points based on speed, cadence, power, etc."""
        df = data.to_dataframe()

        # Get configuration parameters
        stop_speed_threshold = conf.get('stop_speed_threshold_kmh',
                                      config.STOP_SPEED_THRESHOLD_KMH)
        stop_duration_seconds = conf.get('stop_duration_seconds',
                                       config.STOP_DURATION_SECONDS)

        # Mark points with speed below threshold
        df['is_stopped'] = (df['speed_kmh'] < stop_speed_threshold)

        # If cadence data exists, also mark points with low cadence as stopped
        if 'cadence' in df.columns and df['cadence'].notna().any():
            df['is_stopped'] = df['is_stopped'] & (df['cadence'].fillna(1000) < 10)

        # If power data exists, also mark points with low power as stopped
        if 'power' in df.columns and df['power'].notna().any():
            df['is_stopped'] = df['is_stopped'] & (df['power'].fillna(1000) < 30)

        # Default all points are in cruising state
        df['is_cruising'] = True

        # Process continuous stops
        stop_event_active = False
        current_stop_duration = 0
        stop_start_index = -1

        for i in range(len(df)):
            if df.loc[i, 'is_stopped']:
                if not stop_event_active:
                    stop_event_active = True
                    stop_start_index = i
                    current_stop_duration = float(df.loc[i, 'time_diff_seconds']) if pd.notna(df.loc[i, 'time_diff_seconds']) else 0.0
                else:
                    current_stop_duration += float(df.loc[i, 'time_diff_seconds']) if pd.notna(df.loc[i, 'time_diff_seconds']) else 0.0

                if current_stop_duration >= stop_duration_seconds:
                    # Mark the entire stop period as non-cruising
                    df.loc[stop_start_index:i, 'is_cruising'] = False
            else:
                if stop_event_active:
                    stop_event_active = False
                    current_stop_duration = 0
                    stop_start_index = -1

        return RideData.from_dataframe(df)

    @property
    def description(self) -> str:
        return "Mark Stop Points"


class CalculateAcceleration(Processor):
    """Calculate Acceleration"""

    def process(self, data: RideData, conf: Dict[str, Any]) -> RideData:
        """Calculate acceleration and mark points with significant changes"""
        df = data.to_dataframe()

        # Calculate speed difference (m/s)
        df['speed_diff_mps'] = df['speed'].diff().fillna(0)

        # Calculate acceleration (m/s²)
        df['acceleration'] = df.apply(
            lambda row: row['speed_diff_mps'] / row['time_diff_seconds']
            if pd.notna(row['time_diff_seconds']) and row['time_diff_seconds'] > 0 else 0,
            axis=1
        )

        # Handle potential NaN and infinite values
        df['acceleration'] = df['acceleration'].fillna(0)
        df['acceleration'] = df['acceleration'].replace([float('inf'), float('-inf')], 0)

        return RideData.from_dataframe(df)

    @property
    def description(self) -> str:
        return "Calculate Acceleration"


class CalculateSpeedVariability(Processor):
    """Calculate Speed Variability"""

    def process(self, data: RideData, conf: Dict[str, Any]) -> RideData:
        """Calculate rolling standard deviation of speed"""
        df = data.to_dataframe()

        # Get configuration parameters
        rolling_window_speed_std = conf.get('rolling_window_speed_std',
                                         config.ROLLING_WINDOW_SPEED_STD)

        # Ensure window size is an integer and at least 1
        mean_time_diff = df['time_diff_seconds'].mean()
        if pd.isna(mean_time_diff) or mean_time_diff <= 0:
            mean_time_diff = 1.0  # fallback value

        window_size_points_std = max(1, int(rolling_window_speed_std / mean_time_diff))

        # Calculate rolling standard deviation of speed
        df['speed_rolling_std_kmh'] = df['speed_kmh'].rolling(
            window=window_size_points_std,
            center=True
        ).std().bfill().ffill().fillna(0)

        return RideData.from_dataframe(df)

    @property
    def description(self) -> str:
        return "Calculate Speed Variability"


class MarkNonCruising(Processor):
    """Mark Non-Cruising Status"""

    def process(self, data: RideData, conf: Dict[str, Any]) -> RideData:
        """Mark non-cruising status based on acceleration and speed variability"""
        df = data.to_dataframe()

        # Get configuration parameters
        acceleration_threshold = conf.get('acceleration_threshold_mps2',
                                       config.ACCELERATION_THRESHOLD_MPS2)
        speed_std_dev_factor = conf.get('speed_std_dev_threshold_factor',
                                      config.SPEED_STD_DEV_THRESHOLD_FACTOR)
        min_cruising_speed = conf.get('min_cruising_speed_kmh',
                                    config.MIN_CRUISING_SPEED_KMH)

        # Calculate average speed standard deviation for points currently marked as cruising
        if df['is_cruising'].sum() > 0:
            avg_speed_std_cruising = df.loc[df['is_cruising'], 'speed_rolling_std_kmh'].mean()
        else:
            avg_speed_std_cruising = df['speed_rolling_std_kmh'].mean()  # fallback value when no cruising points

        if pd.isna(avg_speed_std_cruising):
            avg_speed_std_cruising = 0.5  # absolute fallback value

        # Mark non-cruising based on acceleration
        df.loc[abs(df['acceleration']) > acceleration_threshold, 'is_cruising'] = False

        # Mark non-cruising based on speed variability
        # Ensure avg_speed_std_cruising is a reasonable positive value
        threshold_std_dev = avg_speed_std_cruising * speed_std_dev_factor if avg_speed_std_cruising > 0.01 else speed_std_dev_factor
        df.loc[df['speed_rolling_std_kmh'] > threshold_std_dev, 'is_cruising'] = False

        # Exclude points below minimum cruising speed
        df.loc[df['speed_kmh'] < min_cruising_speed, 'is_cruising'] = False

        return RideData.from_dataframe(df)

    @property
    def description(self) -> str:
        return "Mark Non-Cruising Status"


class ValidatePowerData(Processor):
    """Power data validation processor"""

    def process(self, data: RideData, conf: Dict[str, Any]) -> RideData:
        """Validate and clean power data"""
        df = data.to_dataframe()
        
        # Skip if no power data
        if 'power' not in df.columns:
            return data
            
        # Remove negative power values
        df.loc[df['power'] < 0, 'power'] = 0
        
        # Remove unreasonably high power values (e.g. spikes)
        max_power_threshold = conf.get('max_power_threshold', config.MAX_POWER_THRESHOLD)
        df.loc[df['power'] > max_power_threshold, 'power'] = np.nan
        
        # Optional: Interpolate small gaps in power data
        if conf.get('interpolate_power_gaps', True):
            gap_size = conf.get('max_power_gap_seconds', 5)
            # Use simple linear interpolation as it doesn't require DatetimeIndex
            df['power'] = df['power'].interpolate(method='linear', limit=gap_size)
            
        return RideData.from_dataframe(df)

    @property
    def description(self) -> str:
        return "Validates and cleans power data"


class PreProcessingPipeline:
    """Data preprocessing pipeline"""

    def __init__(self, processors: Optional[List[Processor]] = None):
        """
        Initialize preprocessing pipeline

        Args:
            processors (List[Processor], optional): List of processors
        """
        self.processors = processors if processors is not None else []

    def add_processor(self, processor: Processor) -> 'PreProcessingPipeline':
        """
        Add processor

        Args:
            processor (Processor): Processor to add

        Returns:
            PreProcessingPipeline: Self, supports chaining
        """
        self.processors.append(processor)
        return self

    def process(self, data: RideData, conf: Optional[Dict[str, Any]] = None) -> RideData:
        """
        Execute preprocessing pipeline

        Args:
            data (RideData): Raw data
            conf (Dict[str, Any], optional): Configuration parameters

        Returns:
            RideData: Processed data
        """
        if conf is None:
            conf = config.get_default_config()

        result = data
        for processor in self.processors:
            result = processor.process(result, conf)

        return result

    @staticmethod
    def create_default_pipeline() -> 'PreProcessingPipeline':
        """Create default preprocessing pipeline"""
        return PreProcessingPipeline([
            ConvertSpeedToKmh(),
            SortAndCalculateTimeDiff(),
            ValidatePowerData(),
            MarkStops(),
            CalculateAcceleration(),
            CalculateSpeedVariability(),
            MarkNonCruising()
        ])
"""
Data models module: Defines core data structures
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd


@dataclass
class Record:
    """Data structure for a single record point"""
    timestamp: datetime
    speed: float  # m/s

    # Optional fields, can be None
    power: Optional[float] = None  # watts
    cadence: Optional[float] = None  # rpm
    distance: Optional[float] = None  # m

    # Fields that may be added during preprocessing
    speed_kmh: Optional[float] = None  # km/h
    time_diff_seconds: Optional[float] = None  # Time difference from the previous record
    acceleration: Optional[float] = None  # m/s^2
    is_stopped: bool = False  # Whether stopped
    is_cruising: bool = True  # Default to cruising state

    # Supports custom fields for easy extension
    extra: Dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key):
        """Supports accessing fields like a dictionary"""
        if hasattr(self, key):
            return getattr(self, key)
        return self.extra.get(key)

    def __setitem__(self, key, value):
        """Supports setting fields like a dictionary"""
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            self.extra[key] = value


@dataclass
class RideData:
    """Collection of ride data"""
    records: List[Record] = field(default_factory=list)

    def to_dataframe(self) -> pd.DataFrame:
        """Converts records to a pandas DataFrame"""
        records_dict = []
        for record in self.records:
            # Merge basic fields and extra fields
            record_dict = {
                k: v for k, v in record.__dict__.items()
                if k != 'extra' and v is not None
            }
            record_dict.update(record.extra)
            records_dict.append(record_dict)

        return pd.DataFrame(records_dict)

    @staticmethod
    def from_dataframe(df: pd.DataFrame) -> 'RideData':
        """Creates RideData from a pandas DataFrame"""
        records = []
        base_fields = {f.name for f in Record.__dataclass_fields__.values()}

        for _, row in df.iterrows():
            # Extract basic fields
            kwargs = {
                field: row[field]
                for field in base_fields
                if field in row and pd.notna(row[field])
            }

            # Extract extra fields
            extra = {
                col: row[col]
                for col in row.index
                if col not in base_fields and pd.notna(row[col])
            }

            if 'extra' not in kwargs:
                kwargs['extra'] = {}
            kwargs['extra'].update(extra)

            records.append(Record(**kwargs))

        return RideData(records=records)

    def __len__(self):
        return len(self.records)
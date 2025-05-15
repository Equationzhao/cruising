"""
Parser module: Responsible for parsing FIT files into RideData
"""

from typing import Optional

from fitparse import FitFile

from models import Record, RideData


def get_field_value(record, field_name, default=None):
    """
    Safely get field value from FIT record.
    
    Args:
        record: FIT file record
        field_name (str): Field name
        default: Default value if field doesn't exist
        
    Returns:
        Any: Field value or default value
    """
    value = record.get_value(field_name)
    return value if value is not None else default


class FitParser:
    """FIT file parser class"""
    
    @staticmethod
    def parse_bytes(fit_data: bytes) -> Optional[RideData]:
        """
        Parse FIT binary data and return RideData object.
        
        Args:
            fit_data (bytes): FIT file binary data
            
        Returns:
            RideData: Contains all parsed riding records
            None: If parsing fails
        """
        try:
            fitfile = FitFile(fit_data)
        except Exception as e:
            return None
        
        records = []
        
        # Iterate through all 'record' type messages
        for record_msg in fitfile.get_messages('record'):
            # Extract basic fields
            timestamp = get_field_value(record_msg, 'timestamp')
            
            # Use enhanced_speed if available, otherwise fall back to speed
            speed = get_field_value(record_msg, 'enhanced_speed')
            if speed is None:
                speed = get_field_value(record_msg, 'speed')
            
            # Only process records with timestamp and speed
            if timestamp is not None and speed is not None:
                record = Record(
                    timestamp=timestamp,
                    speed=speed,
                    power=get_field_value(record_msg, 'power'),
                    cadence=get_field_value(record_msg, 'cadence'),
                    distance=get_field_value(record_msg, 'distance')
                )
                
                # Add extra fields (extensible)
                # Examples: heart rate, altitude, temperature, grade, etc.
                extra_fields = {
                    'heart_rate': get_field_value(record_msg, 'heart_rate'),
                    'altitude': get_field_value(record_msg, 'altitude'),
                    'temperature': get_field_value(record_msg, 'temperature')
                }
                # Filter out None values
                record.extra.update({k: v for k, v in extra_fields.items() if v is not None})
                
                records.append(record)
        
        if not records:
            return None
        
        return RideData(records=records)


# Factory for supporting custom parser formats
class ParserFactory:
    """Parser factory class for creating different types of parsers"""
    
    @staticmethod
    def create(file_type='fit'):
        """
        Create corresponding parser based on file type
        
        Args:
            file_type (str): File type, currently supports 'fit'
            
        Returns:
            Parser instance: Parser object that can parse binary data
            
        Raises:
            ValueError: Unsupported file type
        """
        if file_type.lower() == 'fit':
            return FitParser()
        else:
            raise ValueError(f"Unsupported file type: {file_type}")


def read_fit_file(file_path: str) -> Optional[RideData]:
    """
    Read FIT file and parse into RideData object, separating file reading and parsing operations.
    
    Args:
        file_path (str): FIT file path
        
    Returns:
        RideData: Contains all parsed riding records
        None: If reading or parsing fails
    """
    try:
        with open(file_path, 'rb') as file:
            fit_data = file.read()
        
        parser = FitParser()
        return parser.parse_bytes(fit_data)
    except Exception as e:
        return None

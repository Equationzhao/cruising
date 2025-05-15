"""
Configuration module: Stores all adjustable parameters
"""

# Stop detection parameters
STOP_SPEED_THRESHOLD_KMH = 2.0  # km/h, speeds below this may be considered as stops
STOP_DURATION_SECONDS = 5      # how long a stop must last to be considered valid

# Acceleration/deceleration parameters
ACCELERATION_THRESHOLD_MPS2 = 1.5  # m/s^2, speed change rate threshold
ROLLING_WINDOW_ACCEL = 3       # rolling window size for acceleration calculation (seconds)

# Cruising speed parameters
MIN_CRUISING_SPEED_KMH = 10.0  # data points below this speed won't be included in cruising
ROLLING_WINDOW_SPEED_STD = 5   # rolling window size for speed standard deviation (seconds)
SPEED_STD_DEV_THRESHOLD_FACTOR = 1.5  # factor for determining non-cruising based on speed std dev

# Normalized power parameters
NP_WINDOW_SIZE_SECONDS = 30    # moving average window size for normalized power calculation (seconds)
NP_EXPONENT = 4                # exponent to use in normalized power calculation
MAX_POWER_THRESHOLD = 3000     # maximum reasonable power value (watts)

# The following functions can be used to create configuration objects for more flexible parameter handling
def get_default_config():
    """Returns a dictionary of default configuration parameters"""
    return {
        'stop_speed_threshold_kmh': STOP_SPEED_THRESHOLD_KMH,
        'stop_duration_seconds': STOP_DURATION_SECONDS,
        'acceleration_threshold_mps2': ACCELERATION_THRESHOLD_MPS2,
        'min_cruising_speed_kmh': MIN_CRUISING_SPEED_KMH,
        'rolling_window_accel': ROLLING_WINDOW_ACCEL,
        'rolling_window_speed_std': ROLLING_WINDOW_SPEED_STD,
        'speed_std_dev_threshold_factor': SPEED_STD_DEV_THRESHOLD_FACTOR,
        'np_window_size_seconds': NP_WINDOW_SIZE_SECONDS,
        'np_exponent': NP_EXPONENT,
        'max_power_threshold': MAX_POWER_THRESHOLD
    }

def merge_config(base_config, override_config=None):
    """
    Merge two configurations, overriding base_config parameters with override_config parameters
    
    Args:
        base_config (dict): Base configuration
        override_config (dict, optional): Override configuration
        
    Returns:
        dict: Merged configuration
    """
    if override_config is None:
        return base_config.copy()
    
    merged = base_config.copy()
    for key, value in override_config.items():
        # Update all keys from override_config, not just those in base_config
        merged[key] = value
    
    return merged

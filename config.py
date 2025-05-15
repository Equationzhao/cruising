"""
配置参数模块：存储所有可调整的参数
"""

# 停止检测相关参数
STOP_SPEED_THRESHOLD_KMH = 2.0  # km/h, 低于此速度可能被视为停止
STOP_DURATION_SECONDS = 5      # 持续停止多久才算一次有效停止

# 加速度/减速度相关参数
ACCELERATION_THRESHOLD_MPS2 = 1.5  # m/s^2，速度变化率阈值
ROLLING_WINDOW_ACCEL = 3       # 计算加速度的滚动窗口大小（秒）

# 巡航速度相关参数
MIN_CRUISING_SPEED_KMH = 10.0  # 低于此速度的数据点不会被包括在巡航内
ROLLING_WINDOW_SPEED_STD = 5   # 速度标准差的滚动窗口大小（秒）
SPEED_STD_DEV_THRESHOLD_FACTOR = 1.5  # 速度标准差判定为非巡航的因子

# 以下函数可用于创建配置对象，更灵活地处理参数
def get_default_config():
    """返回默认配置参数的字典"""
    return {
        'stop_speed_threshold_kmh': STOP_SPEED_THRESHOLD_KMH,
        'stop_duration_seconds': STOP_DURATION_SECONDS,
        'acceleration_threshold_mps2': ACCELERATION_THRESHOLD_MPS2,
        'min_cruising_speed_kmh': MIN_CRUISING_SPEED_KMH,
        'rolling_window_accel': ROLLING_WINDOW_ACCEL,
        'rolling_window_speed_std': ROLLING_WINDOW_SPEED_STD,
        'speed_std_dev_threshold_factor': SPEED_STD_DEV_THRESHOLD_FACTOR
    }

def merge_config(base_config, override_config=None):
    """
    合并两个配置，用 override_config 覆盖 base_config 的同名参数
    
    Args:
        base_config (dict): 基础配置
        override_config (dict, optional): 覆盖配置
        
    Returns:
        dict: 合并后的配置
    """
    if override_config is None:
        return base_config.copy()
    
    merged = base_config.copy()
    for key, value in override_config.items():
        if key in merged:
            merged[key] = value
    
    return merged

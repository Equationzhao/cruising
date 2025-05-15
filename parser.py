"""
解析器模块：负责将FIT文件解析为RideData
"""

from typing import Optional

from fitparse import FitFile

from models import Record, RideData


def get_field_value(record, field_name, default=None):
    """
    安全地从FIT记录中获取字段值。
    
    Args:
        record: FIT文件记录
        field_name (str): 字段名称
        default: 若字段不存在时返回的默认值
        
    Returns:
        任意类型: 字段值或默认值
    """
    value = record.get_value(field_name)
    return value if value is not None else default


class FitParser:
    """FIT文件解析类"""
    
    @staticmethod
    def parse_bytes(fit_data: bytes) -> Optional[RideData]:
        """
        解析FIT二进制数据并返回RideData对象。
        
        Args:
            fit_data (bytes): FIT文件的二进制数据
            
        Returns:
            RideData: 包含解析出的所有骑行记录
            None: 解析失败
        """
        try:
            fitfile = FitFile(fit_data)
        except Exception as e:
            print(f"错误：无法解析FIT数据: {e}")
            return None
        
        records = []
        print("解析FIT数据...")
        
        # 遍历所有'record'类型的消息
        for record_msg in fitfile.get_messages('record'):
            # 提取基本字段
            timestamp = get_field_value(record_msg, 'timestamp')
            
            # 优先使用 enhanced_speed，如果没有则回退到 speed
            speed = get_field_value(record_msg, 'enhanced_speed')
            if speed is None:
                speed = get_field_value(record_msg, 'speed')
            
            # 只处理有时间戳和速度的记录
            if timestamp is not None and speed is not None:
                record = Record(
                    timestamp=timestamp,
                    speed=speed,
                    power=get_field_value(record_msg, 'power'),
                    cadence=get_field_value(record_msg, 'cadence'),
                    distance=get_field_value(record_msg, 'distance')
                )
                
                # 添加额外字段（可扩展）
                # 例如：心率、海拔、温度、坡度等
                extra_fields = {
                    'heart_rate': get_field_value(record_msg, 'heart_rate'),
                    'altitude': get_field_value(record_msg, 'altitude'),
                    'temperature': get_field_value(record_msg, 'temperature')
                }
                # 过滤掉None值
                record.extra.update({k: v for k, v in extra_fields.items() if v is not None})
                
                records.append(record)
        
        if not records:
            print("错误：FIT文件中没有找到有效的骑行记录数据。")
            return None
        
        return RideData(records=records)


# 支持自定义解析器格式的工厂
class ParserFactory:
    """解析器工厂类，用于创建不同类型的解析器"""
    
    @staticmethod
    def create(file_type='fit'):
        """
        根据文件类型创建对应的解析器
        
        Args:
            file_type (str): 文件类型，目前支持'fit'
            
        Returns:
            解析器实例: 可以解析二进制数据的解析器对象
            
        Raises:
            ValueError: 不支持的文件类型
        """
        if file_type.lower() == 'fit':
            return FitParser()
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")


def read_fit_file(file_path: str) -> Optional[RideData]:
    """
    读取FIT文件并解析为RideData对象，分离文件读取和解析操作。
    
    Args:
        file_path (str): FIT文件路径
        
    Returns:
        RideData: 包含解析出的所有骑行记录
        None: 读取或解析失败
    """
    try:
        with open(file_path, 'rb') as file:
            fit_data = file.read()
        
        parser = FitParser()
        return parser.parse_bytes(fit_data)
    except Exception as e:
        print(f"错误：无法读取FIT文件 '{file_path}': {e}")
        return None

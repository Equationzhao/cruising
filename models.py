"""
数据模型模块：定义核心数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd


@dataclass
class Record:
    """单个记录点的数据结构"""
    timestamp: datetime
    speed: float  # m/s
    
    # 可选字段，可以为None
    power: Optional[float] = None  # watts
    cadence: Optional[float] = None  # rpm
    distance: Optional[float] = None  # m
    
    # 预处理过程中可能添加的字段
    speed_kmh: Optional[float] = None  # km/h
    time_diff_seconds: Optional[float] = None  # 与前一条记录的时间差
    acceleration: Optional[float] = None  # m/s^2
    is_stopped: bool = False  # 是否停止
    is_cruising: bool = True  # 默认为巡航状态
    
    # 支持自定义字段，方便扩展
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def __getitem__(self, key):
        """支持像字典一样访问字段"""
        if hasattr(self, key):
            return getattr(self, key)
        return self.extra.get(key)
    
    def __setitem__(self, key, value):
        """支持像字典一样设置字段"""
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            self.extra[key] = value


@dataclass
class RideData:
    """骑行数据集合"""
    records: List[Record] = field(default_factory=list)
    
    def to_dataframe(self) -> pd.DataFrame:
        """将记录转换为pandas DataFrame"""
        records_dict = []
        for record in self.records:
            # 合并基本字段和extra字段
            record_dict = {
                k: v for k, v in record.__dict__.items() 
                if k != 'extra' and v is not None
            }
            record_dict.update(record.extra)
            records_dict.append(record_dict)
        
        return pd.DataFrame(records_dict)
    
    @staticmethod
    def from_dataframe(df: pd.DataFrame) -> 'RideData':
        """从pandas DataFrame创建RideData"""
        records = []
        base_fields = {f.name for f in Record.__dataclass_fields__.values()}
        
        for _, row in df.iterrows():
            # 提取基本字段
            kwargs = {
                field: row[field] 
                for field in base_fields 
                if field in row and pd.notna(row[field])
            }
            
            # 提取额外字段
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

"""
预处理模块：提供可插拔的数据预处理流水线
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

import config
from models import RideData


class Processor(ABC):
    """数据处理器基类，定义接口规范"""
    
    @abstractmethod
    def process(self, data: RideData, conf: Dict[str, Any]) -> RideData:
        """
        处理数据
        
        Args:
            data (RideData): 待处理数据
            conf (Dict[str, Any]): 配置参数
            
        Returns:
            RideData: 处理后的数据
        """
        pass
    
    @property
    def description(self) -> str:
        """处理器描述"""
        return "数据处理器"


class ConvertSpeedToKmh(Processor):
    """速度单位转换处理器：m/s → km/h"""
    
    def process(self, data: RideData, conf: Dict[str, Any]) -> RideData:
        """将速度从m/s转换为km/h"""
        for record in data.records:
            record.speed_kmh = record.speed * 3.6
        return data
    
    @property
    def description(self) -> str:
        return "速度单位转换：m/s → km/h"


class SortAndCalculateTimeDiff(Processor):
    """按时间排序并计算时间差"""
    
    def process(self, data: RideData, conf: Dict[str, Any]) -> RideData:
        """按时间戳排序并计算连续记录间的时间差"""
        df = data.to_dataframe()
        
        # 按时间戳排序
        df = df.sort_values(by='timestamp').reset_index(drop=True)
        
        # 计算时间差（秒）
        df['time_diff_seconds'] = df['timestamp'].diff().dt.total_seconds()
        
        # 处理第一行时间差为NaN的情况
        if len(df) > 1 and pd.isna(df.loc[0, 'time_diff_seconds']):
            common_diff = df['time_diff_seconds'].median()
            df.loc[0, 'time_diff_seconds'] = common_diff if pd.notna(common_diff) and common_diff > 0 else 1.0
        
        # 计算累积时间
        df['cumulative_time_seconds'] = df['time_diff_seconds'].cumsum().fillna(0)
        
        return RideData.from_dataframe(df)
    
    @property
    def description(self) -> str:
        return "按时间排序并计算时间差"


class MarkStops(Processor):
    """标记停止点"""
    
    def process(self, data: RideData, conf: Dict[str, Any]) -> RideData:
        """根据速度、踏频、功率等标记停止点"""
        df = data.to_dataframe()
        
        # 获取配置参数
        stop_speed_threshold = conf.get('stop_speed_threshold_kmh', 
                                      config.STOP_SPEED_THRESHOLD_KMH)
        stop_duration_seconds = conf.get('stop_duration_seconds', 
                                       config.STOP_DURATION_SECONDS)
        
        # 标记速度低于阈值的点
        df['is_stopped'] = (df['speed_kmh'] < stop_speed_threshold)
        
        # 如果有踏频数据，将踏频低于阈值的点也标记为停止
        if 'cadence' in df.columns and df['cadence'].notna().any():
            df['is_stopped'] = df['is_stopped'] & (df['cadence'].fillna(1000) < 10)
        
        # 如果有功率数据，将功率低于阈值的点也标记为停止
        if 'power' in df.columns and df['power'].notna().any():
            df['is_stopped'] = df['is_stopped'] & (df['power'].fillna(1000) < 30)
        
        # 默认所有点都是巡航状态
        df['is_cruising'] = True
        
        # 处理连续停止
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
                    # 将整个停止时段标记为非巡航
                    df.loc[stop_start_index:i, 'is_cruising'] = False
            else:
                if stop_event_active:
                    stop_event_active = False
                    current_stop_duration = 0
                    stop_start_index = -1
        
        return RideData.from_dataframe(df)
    
    @property
    def description(self) -> str:
        return "标记停止点"


class CalculateAcceleration(Processor):
    """计算加速度"""
    
    def process(self, data: RideData, conf: Dict[str, Any]) -> RideData:
        """计算加速度并标记剧烈变化点"""
        df = data.to_dataframe()
        
        # 计算速度差异 (m/s)
        df['speed_diff_mps'] = df['speed'].diff().fillna(0)
        
        # 计算加速度 (m/s²)
        df['acceleration'] = df.apply(
            lambda row: row['speed_diff_mps'] / row['time_diff_seconds']
            if pd.notna(row['time_diff_seconds']) and row['time_diff_seconds'] > 0 else 0,
            axis=1
        )
        
        # 处理潜在的NaN和无穷大值
        df['acceleration'] = df['acceleration'].fillna(0)
        df['acceleration'] = df['acceleration'].replace([float('inf'), float('-inf')], 0)
        
        return RideData.from_dataframe(df)
    
    @property
    def description(self) -> str:
        return "计算加速度"


class CalculateSpeedVariability(Processor):
    """计算速度变异性"""
    
    def process(self, data: RideData, conf: Dict[str, Any]) -> RideData:
        """计算速度的滚动标准差"""
        df = data.to_dataframe()
        
        # 获取配置参数
        rolling_window_speed_std = conf.get('rolling_window_speed_std', 
                                         config.ROLLING_WINDOW_SPEED_STD)
        
        # 确保窗口大小是整数且至少为1
        mean_time_diff = df['time_diff_seconds'].mean()
        if pd.isna(mean_time_diff) or mean_time_diff <= 0:
            mean_time_diff = 1.0  # 回退值
        
        window_size_points_std = max(1, int(rolling_window_speed_std / mean_time_diff))
        
        # 计算速度的滚动标准差
        df['speed_rolling_std_kmh'] = df['speed_kmh'].rolling(
            window=window_size_points_std,
            center=True
        ).std().bfill().ffill().fillna(0)
        
        return RideData.from_dataframe(df)
    
    @property
    def description(self) -> str:
        return "计算速度变异性"


class MarkNonCruising(Processor):
    """标记非巡航状态"""
    
    def process(self, data: RideData, conf: Dict[str, Any]) -> RideData:
        """根据加速度和速度变异性标记非巡航状态"""
        df = data.to_dataframe()
        
        # 获取配置参数
        acceleration_threshold = conf.get('acceleration_threshold_mps2', 
                                       config.ACCELERATION_THRESHOLD_MPS2)
        speed_std_dev_factor = conf.get('speed_std_dev_threshold_factor', 
                                      config.SPEED_STD_DEV_THRESHOLD_FACTOR)
        min_cruising_speed = conf.get('min_cruising_speed_kmh', 
                                    config.MIN_CRUISING_SPEED_KMH)
        
        # 计算当前标记为巡航的点的平均速度标准差
        if df['is_cruising'].sum() > 0:
            avg_speed_std_cruising = df.loc[df['is_cruising'], 'speed_rolling_std_kmh'].mean()
        else:
            avg_speed_std_cruising = df['speed_rolling_std_kmh'].mean()  # 没有巡航点时的回退值
        
        if pd.isna(avg_speed_std_cruising):
            avg_speed_std_cruising = 0.5  # 绝对回退值
        
        # 根据加速度标记非巡航
        df.loc[abs(df['acceleration']) > acceleration_threshold, 'is_cruising'] = False
        
        # 根据速度变异性标记非巡航
        # 确保avg_speed_std_cruising是合理的正值
        threshold_std_dev = avg_speed_std_cruising * speed_std_dev_factor if avg_speed_std_cruising > 0.01 else speed_std_dev_factor
        df.loc[df['speed_rolling_std_kmh'] > threshold_std_dev, 'is_cruising'] = False
        
        # 排除低于最低巡航速度的点
        df.loc[df['speed_kmh'] < min_cruising_speed, 'is_cruising'] = False
        
        return RideData.from_dataframe(df)
    
    @property
    def description(self) -> str:
        return "标记非巡航状态"


class PreProcessingPipeline:
    """数据预处理流水线"""
    
    def __init__(self, processors: Optional[List[Processor]] = None):
        """
        初始化预处理流水线
        
        Args:
            processors (List[Processor], optional): 处理器列表
        """
        self.processors = processors if processors is not None else []
    
    def add_processor(self, processor: Processor) -> 'PreProcessingPipeline':
        """
        添加处理器
        
        Args:
            processor (Processor): 处理器
            
        Returns:
            PreProcessingPipeline: 自身，支持链式调用
        """
        self.processors.append(processor)
        return self
    
    def process(self, data: RideData, conf: Optional[Dict[str, Any]] = None) -> RideData:
        """
        执行预处理流水线
        
        Args:
            data (RideData): 原始数据
            conf (Dict[str, Any], optional): 配置参数
            
        Returns:
            RideData: 处理后的数据
        """
        if conf is None:
            conf = config.get_default_config()
        
        result = data
        for processor in self.processors:
            print(f"执行: {processor.description}")
            result = processor.process(result, conf)
        
        return result
    
    @staticmethod
    def create_default_pipeline() -> 'PreProcessingPipeline':
        """创建默认预处理流水线"""
        return PreProcessingPipeline([
            ConvertSpeedToKmh(),
            SortAndCalculateTimeDiff(),
            MarkStops(),
            CalculateAcceleration(),
            CalculateSpeedVariability(),
            MarkNonCruising()
        ])

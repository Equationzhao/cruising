"""
计算模块：实现巡航速度计算逻辑
"""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from models import RideData


class CruisingSpeedCalculator:
    """巡航速度计算器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化计算器
        
        Args:
            config (Dict[str, Any], optional): 配置参数
        """
        self.config = config if config is not None else {}
    
    def calculate(self, data: RideData) -> Dict[str, Any]:
        """
        计算巡航速度和相关指标
        
        Args:
            data (RideData): 已处理好的数据
            
        Returns:
            Dict[str, Any]: 计算结果，包含巡航速度和其他指标
        """
        df = data.to_dataframe()
        
        # 提取巡航数据
        cruising_data = df[df['is_cruising']].copy()
        
        if cruising_data.empty:
            print("警告：在当前阈值下未识别出巡航数据段。")
            self._print_debug_info(df)
            return {
                'cruising_speed': None,
                'success': False,
                'message': '未识别出巡航数据'
            }
        
        # 计算总巡航时间
        cruising_total_time_seconds = cruising_data['time_diff_seconds'].sum()
        
        if cruising_total_time_seconds <= 0:
            print("警告：总巡航时间为零或负值，无法计算加权平均速度。")
            return {
                'cruising_speed': None,
                'avg_speed': cruising_data['speed_kmh'].mean() if not cruising_data.empty else None,
                'success': False,
                'message': '总巡航时间异常'
            }
        
        # 计算时间加权巡航速度
        weighted_cruising_speed_kmh = (
            cruising_data['speed_kmh'] * cruising_data['time_diff_seconds']
        ).sum() / cruising_total_time_seconds
        
        # 准备结果
        result = {
            'cruising_speed': weighted_cruising_speed_kmh,
            'avg_speed': cruising_data['speed_kmh'].mean(),
            'cruising_points': len(cruising_data),
            'total_points': len(df),
            'cruising_time_seconds': cruising_total_time_seconds,
            'success': True
        }
        
        # 添加可选指标
        self._add_optional_metrics(result, cruising_data, cruising_total_time_seconds)
        
        return result
    
    def _add_optional_metrics(self, result: Dict[str, Any], 
                             cruising_data: pd.DataFrame, 
                             cruising_total_time_seconds: float) -> None:
        """添加可选的计算指标（如功率、踏频等）"""
        
        # 计算平均巡航功率（如果有）
        if 'power' in cruising_data.columns and cruising_data['power'].notna().any():
            result['avg_power'] = (
                cruising_data['power'] * cruising_data['time_diff_seconds']
            ).sum() / cruising_total_time_seconds
        
        # 计算平均巡航踏频（如果有）
        if 'cadence' in cruising_data.columns and cruising_data['cadence'].notna().any():
            result['avg_cadence'] = (
                cruising_data['cadence'] * cruising_data['time_diff_seconds']
            ).sum() / cruising_total_time_seconds
        
        # 计算平均巡航心率（如果有）
        if 'heart_rate' in cruising_data.columns and cruising_data['heart_rate'].notna().any():
            result['avg_heart_rate'] = (
                cruising_data['heart_rate'] * cruising_data['time_diff_seconds']
            ).sum() / cruising_total_time_seconds
    
    def _print_debug_info(self, df: pd.DataFrame) -> None:
        """打印调试信息"""
        print("\n数据概览（用于阈值调试）:")
        print(f"  整体平均速度 (km/h): {df['speed_kmh'].mean():.2f}")
        
        if not df[df['is_stopped']].empty:
            print(f"  '停止'点的平均速度 (km/h): {df[df['is_stopped']]['speed_kmh'].mean():.2f}")
        
        print(f"  最大绝对加速度 (m/s^2): {df['acceleration'].abs().max():.2f}")
        
        if 'speed_rolling_std_kmh' in df.columns:
            print(f"  最大速度滚动标准差 (km/h): {df['speed_rolling_std_kmh'].max():.2f}")
        
        if 'power' in df.columns and df['power'].notna().any():
            print(f"  整体平均功率 (W): {df['power'].mean():.2f}")
    

# 工厂函数，创建不同类型的计算器
def create_calculator(calculator_type='cruising_speed', config=None):
    """
    创建一个计算器实例
    
    Args:
        calculator_type (str): 计算器类型
        config (Dict[str, Any], optional): 配置参数
        
    Returns:
        计算器实例
    """
    if calculator_type == 'cruising_speed':
        return CruisingSpeedCalculator(config)
    else:
        raise ValueError(f"不支持的计算器类型: {calculator_type}")

"""
Streamlit应用入口：巡航速度分析工具
"""

import io
import tempfile
from datetime import datetime

import pandas as pd
import streamlit as st
import plotly.express as px

import config
from compute import create_calculator
from models import RideData
from parser import FitParser
from preprocess import PreProcessingPipeline
import visualization


# 设置页面配置
st.set_page_config(
    page_title="巡航速度分析工具",
    page_icon="🚴‍♂️",
    layout="wide"
)


def process_uploaded_file(uploaded_file, user_config):
    """
    处理上传的FIT文件并计算巡航速度
    
    Args:
        uploaded_file: 上传的文件对象
        user_config: 用户自定义配置
        
    Returns:
        tuple: (结果字典, 处理后的DataFrame)
    """
    try:
        # 读取上传的文件数据
        bytes_data = uploaded_file.getvalue()
        
        # 解析FIT数据
        parser = FitParser()
        ride_data = parser.parse_bytes(bytes_data)
        
        if ride_data is None:
            return {"success": False, "message": "无法解析FIT文件数据"}, None
        
        # 显示原始数据点数量
        st.info(f"原始数据点数量: {len(ride_data.records)}")
        
        # 合并配置
        conf = config.merge_config(
            config.get_default_config(),
            user_config
        )
        
        # 预处理数据
        pipeline = PreProcessingPipeline.create_default_pipeline()
        processed_data = pipeline.process(ride_data, conf)
        
        # 计算巡航速度
        calculator = create_calculator('cruising_speed', conf)
        result = calculator.calculate(processed_data)
        
        # 转换为DataFrame以便可视化
        df = processed_data.to_dataframe()
        
        return result, df
        
    except Exception as e:
        st.error(f"处理文件时出错: {str(e)}")
        return {"success": False, "message": f"处理出错: {str(e)}"}, None


def show_results(result, df):
    """
    显示计算结果和可视化图表
    
    Args:
        result: 计算结果字典
        df: 处理后的DataFrame
    """
    if not result['success']:
        st.error(f"计算失败: {result.get('message', '未知错误')}")
        return
    
    # 显示主要结果
    st.success(f"### 巡航速度: {result['cruising_speed']:.2f} km/h")
    
    # 显示其他指标
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("平均速度", f"{result.get('avg_speed', 0):.2f} km/h")
    if 'avg_power' in result:
        with col2:
            st.metric("平均功率", f"{result['avg_power']:.2f} W")
    if 'avg_cadence' in result:
        with col3:
            st.metric("平均踏频", f"{result['avg_cadence']:.2f} rpm")
    
    # 显示骑行概览
    st.subheader("骑行概览")
    summary_chart = visualization.create_summary_charts(df, result)
    st.plotly_chart(summary_chart, use_container_width=True)
    
    # 显示图表
    st.subheader("速度曲线")
    speed_chart = visualization.create_speed_time_chart(df)
    st.plotly_chart(speed_chart, use_container_width=True)
    
    st.subheader("速度分布")
    dist_chart = visualization.create_speed_distribution(df)
    st.plotly_chart(dist_chart, use_container_width=True)
    
    # 提供数据下载选项
    if st.button("导出处理后的数据"):
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="下载CSV",
            data=csv_data,
            file_name=f"cruising_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )


def main():
    """主函数：Streamlit应用入口"""
    st.title("🚴‍♂️ 巡航速度分析工具")
    
    st.write("""
    此工具可分析骑行数据并计算巡航速度。上传您的FIT文件并调整参数以获得结果。
    """)
    
    # 侧边栏：参数设置
    with st.sidebar:
        st.header("参数设置")
        
        # 基本参数
        st.subheader("基本参数")
        stop_speed = st.slider(
            "停止速度阈值 (km/h)", 
            min_value=0.5, 
            max_value=5.0, 
            value=config.STOP_SPEED_THRESHOLD_KMH,
            help="低于此速度被视为可能停止"
        )
        
        min_cruising_speed = st.slider(
            "最小巡航速度 (km/h)", 
            min_value=5.0, 
            max_value=20.0, 
            value=config.MIN_CRUISING_SPEED_KMH,
            help="低于此速度的数据点将不被视为巡航"
        )
        
        accel_threshold = st.slider(
            "加速度阈值 (m/s²)", 
            min_value=0.5, 
            max_value=3.0, 
            value=config.ACCELERATION_THRESHOLD_MPS2,
            help="超过此加速度的点不被视为巡航"
        )
        
        # 高级参数（可折叠）
        with st.expander("高级参数"):
            stop_duration = st.slider(
                "停止持续时间 (秒)", 
                min_value=1, 
                max_value=10, 
                value=config.STOP_DURATION_SECONDS,
                help="持续停止多久才算一次有效停止"
            )
            
            rolling_window = st.slider(
                "滚动窗口大小 (秒)", 
                min_value=1, 
                max_value=10, 
                value=config.ROLLING_WINDOW_SPEED_STD,
                help="计算速度标准差的窗口大小"
            )
            
            std_dev_factor = st.slider(
                "速度标准差阈值因子", 
                min_value=0.5, 
                max_value=3.0, 
                value=config.SPEED_STD_DEV_THRESHOLD_FACTOR,
                help="速度波动判定为非巡航的因子"
            )
        
        # 收集用户配置
        user_config = {
            'stop_speed_threshold_kmh': stop_speed,
            'min_cruising_speed_kmh': min_cruising_speed,
            'acceleration_threshold_mps2': accel_threshold,
            'stop_duration_seconds': stop_duration,
            'rolling_window_speed_std': rolling_window,
            'speed_std_dev_threshold_factor': std_dev_factor
        }
    
    # 主区域：文件上传和结果显示
    uploaded_file = st.file_uploader("上传FIT文件", type=['fit'])
    
    if uploaded_file is not None:
        # 分析按钮
        if st.button("分析骑行数据"):
            with st.spinner('处理数据中...'):
                # 处理文件
                result, df = process_uploaded_file(uploaded_file, user_config)
                
                if df is not None:
                    # 显示结果
                    show_results(result, df)


if __name__ == "__main__":
    main()

"""
可视化模块：提供数据可视化功能
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_speed_time_chart(df: pd.DataFrame) -> go.Figure:
    """
    创建速度-时间曲线图
    
    Args:
        df (pd.DataFrame): 包含速度、时间和巡航标记的DataFrame
        
    Returns:
        plotly.graph_objects.Figure: 速度-时间图表
    """
    # 创建图表
    fig = px.line(df, x='timestamp', y='speed_kmh')
    
    # 添加巡航段高亮
    cruising_df = df[df['is_cruising']]
    fig.add_scatter(
        x=cruising_df['timestamp'], 
        y=cruising_df['speed_kmh'],
        mode='markers',
        marker=dict(color='green', size=5),
        name='巡航段'
    )
    
    # 设置布局
    fig.update_layout(
        title='骑行速度曲线',
        xaxis_title='时间',
        yaxis_title='速度 (km/h)',
        legend_title='数据类型',
        hovermode='closest'
    )
    
    return fig


def create_speed_distribution(df: pd.DataFrame) -> go.Figure:
    """
    创建速度分布直方图
    
    Args:
        df (pd.DataFrame): 包含速度和巡航标记的DataFrame
        
    Returns:
        plotly.graph_objects.Figure: 速度分布图表
    """
    # 创建子图
    fig = make_subplots(rows=1, cols=2, subplot_titles=('全部数据', '仅巡航段'))
    
    # 全部数据的速度分布
    fig.add_trace(
        go.Histogram(
            x=df['speed_kmh'],
            nbinsx=30,
            name='全部',
            marker_color='blue',
            opacity=0.7
        ),
        row=1, col=1
    )
    
    # 仅巡航段的速度分布
    fig.add_trace(
        go.Histogram(
            x=df[df['is_cruising']]['speed_kmh'],
            nbinsx=30,
            name='巡航',
            marker_color='green',
            opacity=0.7
        ),
        row=1, col=2
    )
    
    # 设置布局
    fig.update_layout(
        title='速度分布直方图',
        xaxis_title='速度 (km/h)', 
        yaxis_title='频次',
        bargap=0.1,
        showlegend=False
    )
    
    fig.update_xaxes(title_text='速度 (km/h)', row=1, col=1)
    fig.update_xaxes(title_text='速度 (km/h)', row=1, col=2)
    fig.update_yaxes(title_text='频次', row=1, col=1)
    
    return fig


def create_summary_charts(df: pd.DataFrame, result: dict) -> go.Figure:
    """
    创建骑行概览图表
    
    Args:
        df (pd.DataFrame): 处理后的DataFrame
        result (dict): 计算结果
        
    Returns:
        plotly.graph_objects.Figure: 概览图表
    """
    # 计算统计数据
    cruising_percentage = (df['is_cruising'].sum() / len(df)) * 100
    
    # 创建子图
    fig = make_subplots(
        rows=1, 
        cols=2,
        specs=[[{"type": "pie"}, {"type": "indicator"}]]
    )
    
    # 添加巡航占比饼图
    fig.add_trace(
        go.Pie(
            labels=['巡航', '非巡航'],
            values=[df['is_cruising'].sum(), len(df) - df['is_cruising'].sum()],
            marker_colors=['green', 'red']
        ),
        row=1, col=1
    )
    
    # 添加巡航速度指示器
    fig.add_trace(
        go.Indicator(
            value=result.get('cruising_speed', 0),
            title={'text': "巡航速度 (km/h)"},
            mode="gauge+number",
            gauge={
                'axis': {'range': [0, max(df['speed_kmh'].max(), 50)]},
                'bar': {'color': "green"},
                'steps': [
                    {'range': [0, result.get('cruising_speed', 0)*0.8], 'color': "lightgray"},
                    {'range': [result.get('cruising_speed', 0)*0.8, result.get('cruising_speed', 0)*1.2], 'color': "gray"}
                ]
            }
        ),
        row=1, col=2
    )
    
    # 设置布局
    fig.update_layout(
        title='骑行概览',
        height=400
    )
    
    return fig

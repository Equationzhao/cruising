"""
Visualization module: Provides data visualization functionality
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_speed_time_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create speed-time curve chart
    
    Args:
        df (pd.DataFrame): DataFrame containing speed, time and cruising markers
        
    Returns:
        plotly.graph_objects.Figure: Speed-time chart
    """
    # Create chart
    fig = px.line(df, x='timestamp', y='speed_kmh')
    
    # Add cruising section highlighting
    cruising_df = df[df['is_cruising']]
    fig.add_scatter(
        x=cruising_df['timestamp'], 
        y=cruising_df['speed_kmh'],
        mode='markers',
        marker=dict(color='green', size=5),
        name='Cruising'
    )
    
    # Set up layout
    fig.update_layout(
        title='Riding Speed Curve',
        xaxis_title='Time',
        yaxis_title='Speed (km/h)',
        legend_title='Data Type',
        hovermode='closest'
    )
    
    return fig


def create_speed_distribution(df: pd.DataFrame) -> go.Figure:
    """
    Create speed distribution histogram
    
    Args:
        df (pd.DataFrame): DataFrame containing speed and cruising markers
        
    Returns:
        plotly.graph_objects.Figure: Speed distribution chart
    """
    # Create subplots
    fig = make_subplots(rows=1, cols=2, subplot_titles=('All Data', 'Cruising Only'))
    
    # Speed distribution of all data
    fig.add_trace(
        go.Histogram(
            x=df['speed_kmh'],
            nbinsx=30,
            name='All',
            marker_color='blue',
            opacity=0.7
        ),
        row=1, col=1
    )
    
    # Speed distribution of cruising sections only
    fig.add_trace(
        go.Histogram(
            x=df[df['is_cruising']]['speed_kmh'],
            nbinsx=30,
            name='Cruising',
            marker_color='green',
            opacity=0.7
        ),
        row=1, col=2
    )
    
    # Set layout
    fig.update_layout(
        title='Speed Distribution Histogram',
        xaxis_title='Speed (km/h)', 
        yaxis_title='Frequency',
        bargap=0.1,
        showlegend=False
    )
    
    fig.update_xaxes(title_text='Speed (km/h)', row=1, col=1)
    fig.update_xaxes(title_text='Speed (km/h)', row=1, col=2)
    fig.update_yaxes(title_text='Frequency', row=1, col=1)
    
    return fig


def create_summary_charts(df: pd.DataFrame, result: dict) -> go.Figure:
    """
    Create ride overview charts
    
    Args:
        df (pd.DataFrame): Processed DataFrame
        result (dict): Calculation results
        
    Returns:
        plotly.graph_objects.Figure: Overview charts
    """
    # Create subplots
    fig = make_subplots(
        rows=1, 
        cols=2,
        specs=[[{"type": "pie"}, {"type": "indicator"}]]
    )
    
    # Add cruising ratio pie chart
    fig.add_trace(
        go.Pie(
            labels=['Cruising', 'Non-Cruising'],
            values=[df['is_cruising'].sum(), len(df) - df['is_cruising'].sum()],
            marker_colors=['green', 'red']
        ),
        row=1, col=1
    )
    
    # Add cruising speed indicator
    fig.add_trace(
        go.Indicator(
            value=result.get('cruising_speed', 0),
            title={'text': "Cruising Speed (km/h)"},
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
    
    # Set layout
    fig.update_layout(
        title='Ride Overview',
        height=400
    )
    
    return fig


def create_power_analysis_chart(df: pd.DataFrame, result: dict) -> go.Figure:
    """
    Create power analysis chart with raw power, 30s avg power, and NP
    
    Args:
        df (pd.DataFrame): DataFrame containing power data
        result (dict): Calculation results with NP
        
    Returns:
        plotly.graph_objects.Figure: Power analysis chart
    """
    # Skip if no power data
    if 'power' not in df.columns:
        fig = go.Figure()
        fig.update_layout(
            title='Power Analysis (No power data available)',
            xaxis_title='Time',
            yaxis_title='Power (W)'
        )
        return fig
    
    # Create chart
    fig = go.Figure()
    
    # Add raw power data
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['power'],
            mode='lines',
            line=dict(color='lightblue', width=1),
            name='Instant Power'
        )
    )
    
    # Add 30s rolling average power if available
    if 'power_30s_avg' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['power_30s_avg'],
                mode='lines',
                line=dict(color='blue', width=2),
                name='30s Avg Power'
            )
        )
    
    # Add NP horizontal line
    if result.get('normalized_power'):
        fig.add_shape(
            type="line",
            x0=df['timestamp'].min(),
            y0=result['normalized_power'],
            x1=df['timestamp'].max(),
            y1=result['normalized_power'],
            line=dict(color="red", width=2, dash="dash"),
        )
        
        # Add NP text label
        fig.add_annotation(
            x=df['timestamp'].max(),
            y=result['normalized_power'],
            text=f"NP: {result['normalized_power']:.0f}W",
            showarrow=False,
            yshift=10,
            font=dict(color="red")
        )
    
    # Set up layout
    fig.update_layout(
        title='Power Analysis',
        xaxis_title='Time',
        yaxis_title='Power (W)',
        legend_title='Data Type',
        hovermode='closest'
    )
    
    return fig


def create_power_distribution(df: pd.DataFrame, result: dict) -> go.Figure:
    """
    Create power distribution histogram
    
    Args:
        df (pd.DataFrame): DataFrame containing power data
        result (dict): Calculation results
        
    Returns:
        plotly.graph_objects.Figure: Power distribution chart
    """
    # Skip if no power data
    if 'power' not in df.columns:
        fig = go.Figure()
        fig.update_layout(
            title='Power Distribution (No power data available)',
            xaxis_title='Power (W)',
            yaxis_title='Frequency'
        )
        return fig
    
    # Create subplots
    fig = make_subplots(rows=1, cols=1, subplot_titles=('Power Distribution',))
    
    # Power distribution histogram
    fig.add_trace(
        go.Histogram(
            x=df['power'],
            nbinsx=30,
            name='Power',
            marker_color='blue',
            opacity=0.7
        )
    )
    
    # Add vertical lines for avg power and NP
    if 'avg_power' in result and result['avg_power'] is not None:
        fig.add_vline(
            x=result['avg_power'], 
            line_dash="solid",
            line_color="green",
            annotation_text=f"Avg: {result['avg_power']:.0f}W",
            annotation_position="top right"
        )
    
    if 'normalized_power' in result and result['normalized_power'] is not None:
        fig.add_vline(
            x=result['normalized_power'], 
            line_dash="dash",
            line_color="red",
            annotation_text=f"NP: {result['normalized_power']:.0f}W",
            annotation_position="top right"
        )
    
    # Set layout
    fig.update_layout(
        title='Power Distribution',
        xaxis_title='Power (W)', 
        yaxis_title='Frequency',
        bargap=0.1,
        showlegend=False
    )
    
    return fig

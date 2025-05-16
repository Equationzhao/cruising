"""
Streamlit application entry: Cruising Speed Analysis Tool
"""

from parser import FitParser

import streamlit as st

import config
import visualization
from compute import create_calculator
from models import RideData
from preprocess import PreProcessingPipeline

# Set page configuration
st.set_page_config(
    page_title="Cruising Speed Analysis Tool",
    page_icon="🚴‍♂️",
    layout="wide"
)


def process_uploaded_file(uploaded_file, user_config):
    """
    Process the uploaded FIT file and calculate cruising speed

    Args:
        uploaded_file: Uploaded file object
        user_config: User-defined configuration

    Returns:
        tuple: (results dictionary, processed DataFrame)
    """
    try:
        # Read uploaded file data
        bytes_data = uploaded_file.getvalue()

        # Parse FIT data
        parser = FitParser()
        ride_data = parser.parse_bytes(bytes_data)

        if ride_data is None:
            return {"success": False, "message": "Failed to parse FIT file data"}, None

        # Display original data point count
        st.info(f"Original data points: {len(ride_data.records)}")

        # Merge configurations
        conf = config.merge_config(
            config.get_default_config(),
            user_config
        )

        # Preprocess data
        pipeline = PreProcessingPipeline.create_default_pipeline()
        processed_data = pipeline.process(ride_data, conf)

        # Calculate cruising speed
        cruising_calculator = create_calculator('cruising_speed', conf)
        cruising_result = cruising_calculator.calculate(processed_data)
        
        # Calculate normalized power if configuration available
        np_calculator = create_calculator('normalized_power', conf)
        np_result = np_calculator.calculate(processed_data)
        
        # Merge results
        result = {**cruising_result}
        
        # Only merge NP results if they were successful
        if np_result.get('success', False):
            result.update({
                'normalized_power': np_result.get('normalized_power'),
                'intensity_factor': np_result.get('intensity_factor'),
                'np_to_avg_ratio': np_result.get('np_to_avg_ratio'),
            })

        # Convert to DataFrame for visualization
        df = processed_data.to_dataframe()

        return result, df

    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return {"success": False, "message": f"Processing error: {str(e)}"}, None


def show_results(result, df):
    """
    Display calculation results and visualizations

    Args:
        result: Calculation results dictionary
        df: Processed DataFrame
    """
    if not result['success']:
        st.error(f"Calculation failed: {result.get('message', 'Unknown error')}")
        return
    
    # Create tabs for different types of analysis
    tab1, tab2 = st.tabs(["Speed Analysis", "Power Analysis"])
    
    with tab1:
        # Display main result
        st.success(f"### Cruising Speed: {result['cruising_speed']:.2f} km/h")

        # Display other metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Average Speed", f"{result.get('avg_speed', 0):.2f} km/h")
        if 'avg_power' in result:
            with col2:
                st.metric("Average Power", f"{result['avg_power']:.2f} W")
        if 'avg_cadence' in result:
            with col3:
                st.metric("Average Cadence", f"{result['avg_cadence']:.2f} rpm")

        # Display ride overview
        st.subheader("Ride Overview")
        summary_chart = visualization.create_summary_charts(df, result)
        st.plotly_chart(summary_chart, use_container_width=True)

        # Display charts
        st.subheader("Speed Timeline")
        speed_chart = visualization.create_speed_time_chart(df)
        st.plotly_chart(speed_chart, use_container_width=True)

        st.subheader("Speed Distribution")
        dist_chart = visualization.create_speed_distribution(df)
        st.plotly_chart(dist_chart, use_container_width=True)
    
    with tab2:
        # Display normalized power results
        if result.get('normalized_power') is not None:
            st.success(f"### Normalized Power (NP): {result['normalized_power']:.0f} W")
            
            # Display power metrics
            cols = st.columns(3)
            with cols[0]:
                st.metric("Average Power", f"{result.get('avg_power', 0):.0f} W")
            with cols[1]:
                st.metric("NP/Avg Ratio", f"{result.get('np_to_avg_ratio', 0):.2f}")
            with cols[2]:
                if result.get('intensity_factor') is not None:
                    st.metric("Intensity Factor (IF)", f"{result['intensity_factor']:.2f}")
            
            # Display power charts
            st.subheader("Power Analysis")
            power_chart = visualization.create_power_analysis_chart(df, result)
            st.plotly_chart(power_chart, use_container_width=True)
            
            st.subheader("Power Distribution")
            power_dist_chart = visualization.create_power_distribution(df, result)
            st.plotly_chart(power_dist_chart, use_container_width=True)
        else:
            st.warning("No power data detected. Normalized Power cannot be calculated.")

def main():
    """Main function: Streamlit application entry point"""
    st.title("🚴‍♂️ Cruising Speed Analysis Tool")

    st.write("""
    This tool analyzes cycling data and calculates cruising speed. Upload your FIT file and adjust parameters to get results.
    """)

    # Sidebar: Parameter settings
    with st.sidebar:
        st.header("Parameters")

        # Add tabs for different parameter categories
        param_tab1, param_tab2 = st.tabs(["Speed Analysis", "Power Analysis"])
        
        with param_tab1:
            # Basic speed parameters
            st.subheader("Basic Parameters")
            stop_speed = st.slider(
                "Stop Speed Threshold (km/h)",
                min_value=0.0,
                max_value=20.0,
                value=config.STOP_SPEED_THRESHOLD_KMH,
                help="Speed below this is considered a potential stop"
            )

            min_cruising_speed = st.slider(
                "Minimum Cruising Speed (km/h)",
                min_value=5.0,
                max_value=70.0,
                value=config.MIN_CRUISING_SPEED_KMH,
                help="Data points below this speed won't be considered cruising"
            )

            accel_threshold = st.slider(
                "Acceleration Threshold (m/s²)",
                min_value=0.5,
                max_value=3.0,
                value=config.ACCELERATION_THRESHOLD_MPS2,
                help="Points exceeding this acceleration won't be considered cruising"
            )

            # Advanced speed parameters (collapsible)
            with st.expander("Advanced Speed Parameters"):
                stop_duration = st.slider(
                    "Stop Duration (sec)",
                    min_value=1,
                    max_value=10,
                    value=config.STOP_DURATION_SECONDS,
                    help="How long a stop needs to last to be considered valid"
                )

                rolling_window = st.slider(
                    "Rolling Window Size (sec)",
                    min_value=1,
                    max_value=10,
                    value=config.ROLLING_WINDOW_SPEED_STD,
                    help="Window size for calculating speed standard deviation"
                )

                std_dev_factor = st.slider(
                    "Speed StdDev Threshold Factor",
                    min_value=0.5,
                    max_value=3.0,
                    value=config.SPEED_STD_DEV_THRESHOLD_FACTOR,
                    help="Factor for determining when speed variation is non-cruising"
                )
                
        with param_tab2:
            # Power analysis parameters
            st.subheader("Power Analysis Parameters")
            
            np_window = st.slider(
                "NP Window Size (seconds)",
                min_value=10,
                max_value=60,
                value=config.NP_WINDOW_SIZE_SECONDS,
                help="Moving average window size for normalized power calculation"
            )
            
            ftp = st.number_input(
                "Functional Threshold Power (FTP)",
                min_value=0,
                value=0,
                help="Set your FTP to calculate Intensity Factor (IF), leave at 0 to skip"
            )
            
            # Advanced power parameters
            with st.expander("Advanced Power Parameters"):
                max_power = st.slider(
                    "Maximum Power Threshold (W)",
                    min_value=1000,
                    max_value=5000,
                    value=config.MAX_POWER_THRESHOLD,
                    help="Power values above this threshold will be treated as errors"
                )
                
                interpolate_gaps = st.checkbox(
                    "Interpolate Power Gaps",
                    value=True,
                    help="Automatically fill small gaps in power data"
                )
                
        # Collect user configuration
        user_config = {
            'stop_speed_threshold_kmh': stop_speed,
            'min_cruising_speed_kmh': min_cruising_speed,
            'acceleration_threshold_mps2': accel_threshold,
            'stop_duration_seconds': stop_duration,
            'rolling_window_speed_std': rolling_window,
            'speed_std_dev_threshold_factor': std_dev_factor,
            'np_window_size_seconds': np_window,
            'ftp': ftp if ftp > 0 else None,
            'max_power_threshold': max_power,
            'interpolate_power_gaps': interpolate_gaps
        }

    # Main area: File upload and results display
    uploaded_file = st.file_uploader("Upload FIT File", type=['fit'])

    if uploaded_file is not None:
        # Analyze button
        if st.button("Analyze Ride Data"):
            with st.spinner('Processing data...'):
                # Process file
                result, df = process_uploaded_file(uploaded_file, user_config)

                if df is not None:
                    # Display results
                    show_results(result, df)


if __name__ == "__main__":
    main()